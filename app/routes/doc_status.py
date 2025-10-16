import json
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from rq.job import Job

from app.services.rq_conn import get_queue
from app.services.storage import get_minio_client, get_json_from_minio, BUCKET

router = APIRouter(prefix="/docs", tags=["docs"])


def _job_state(job_id: str) -> str:
    try:
        job = Job.fetch(job_id, connection=get_queue().connection)
        return job.get_status()  # "queued" | "started" | "finished" | "failed" | "deferred" | ...
    except Exception:
        return "unknown"


@router.get("/{doc_id}/status")
def get_doc_status(doc_id: str) -> Dict[str, Any]:
    client = get_minio_client()
    bucket = BUCKET
    manifest_key = f"docs/{doc_id}/manifest.json"

    manifest: Dict[str, Any] = get_json_from_minio(client, bucket, manifest_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="manifest not found")

    chunks: List[Dict[str, Any]] = manifest.get("chunks", [])
    total = len(chunks)
    counts = {"queued": 0, "started": 0, "finished": 0, "failed": 0, "unknown": 0}
    detailed = []

    for ch in chunks:
        st = _job_state(ch.get("job_id"))
        counts[st] = counts.get(st, 0) + 1
        detailed.append({
            "index": ch["index"],
            "range": {"start_page": ch["start_page"], "end_page": ch["end_page"]},
            "job_id": ch.get("job_id"),
            "status": st,
            "expected_key": ch.get("expected_key"),
            "meta_key": ch.get("meta_key"),
        })

    completed = counts.get("finished", 0)
    progress = round(100.0 * completed / max(total, 1), 2)

    return {
        "doc_id": doc_id,
        "total_chunks": total,
        "progress_pct": progress,
        "counts": counts,
        "manifest_key": manifest_key,
        "chunks": detailed,
    }


@router.get("/{doc_id}/chunks")
def list_doc_chunks(doc_id: str) -> Dict[str, Any]:
    client = get_minio_client()
    bucket = BUCKET
    manifest_key = f"docs/{doc_id}/manifest.json"

    manifest: Dict[str, Any] = get_json_from_minio(client, bucket, manifest_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="manifest not found")

    q = get_queue()
    out = []
    for ch in manifest.get("chunks", []):
        st = _job_state(ch.get("job_id"))
        if st == "finished":
            # gunakan proxy agar URL external-friendly
            out.append({
                "index": ch["index"],
                "start_page": ch["start_page"],
                "end_page": ch["end_page"],
                "pdf_key": ch["expected_key"],
                "meta_key": ch["meta_key"],
                "download_pdf": f"/files/proxy?key={ch['expected_key']}",
                "download_meta": f"/files/proxy?key={ch['meta_key']}",
            })

    return {"doc_id": doc_id, "ready_chunks": out}


@router.post("/{doc_id}/retry-failed")
def retry_failed(doc_id: str) -> Dict[str, Any]:
    client = get_minio_client()
    bucket = BUCKET
    manifest_key = f"docs/{doc_id}/manifest.json"
    manifest: Dict[str, Any] = get_json_from_minio(client, bucket, manifest_key)
    if not manifest:
        raise HTTPException(status_code=404, detail="manifest not found")

    q = get_queue()

    retried = []
    for ch in manifest.get("chunks", []):
        st = _job_state(ch.get("job_id"))
        if st == "failed":
            job = q.enqueue(
                "app.worker_tasks.split_pdf_chunk",
                kwargs={
                    "doc_id": doc_id,
                    "original_key": manifest["original_key"],
                    "start_page": ch["start_page"],
                    "end_page": ch["end_page"],
                    "out_key": ch["expected_key"],
                    "meta_key": ch["meta_key"],
                },
                job_id=None,  # biar dapat job_id baru
                description=f"retry-split doc:{doc_id} chunk:{ch['index']}",
            )
            ch["job_id"] = job.id
            retried.append({"index": ch["index"], "new_job_id": job.id})

    # tulis balik manifest hasil update job_id
    client.put_object(
        bucket, manifest_key,
        data=bytes(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8"),
        length=-1, part_size=10 * 1024 * 1024, content_type="application/json"
    )

    return {"doc_id": doc_id, "retried": retried}
