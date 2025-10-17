from typing import List, Dict

from rq import Retry

from app.services.rq_conn import get_queue  # asumsi sudah ada
from app.services.storage import BUCKET, get_minio_client, get_json_from_minio
from app.worker_tasks.extraction_worker_tasks import extract_chunk_pdfplumber_task


def _load_manifest(doc_id: str) -> dict | None:
    client = get_minio_client()
    key = f"docs/{doc_id}/manifest.json"
    return get_json_from_minio(client, BUCKET, key)


def plan_pdfplumber_extraction_jobs(doc_id: str) -> Dict[str, any]:
    """
    Baca manifest → buat job untuk setiap chunk.
    Hasil JSON:
    {
      "doc_id": "...",
      "jobs": [{"chunk_index": 1, "job_id": "...", "out_jsonl_key": "..."}]
    }
    """
    manifest = _load_manifest(doc_id)
    if not manifest:
        raise ValueError(f"Manifest not found for doc_id={doc_id}")

    chunks: List[Dict] = manifest.get("chunks", [])
    q = get_queue("extractions")
    jobs = []

    for ch in chunks:
        idx = ch["index"]
        start_page = ch["start_page"]  # dari manifest split
        expected_pdf_key = ch["expected_key"]  # lokasi chunk pdf
        out_jsonl_key = f"docs/{doc_id}/texts/chunk-{idx:04d}.jsonl"

        payload = {
            "doc_id": doc_id,
            "chunk_index": idx,
            "chunk_pdf_key": expected_pdf_key,
            "out_jsonl_key": out_jsonl_key,
            "page_offset": start_page,
        }

        job = q.enqueue(
            extract_chunk_pdfplumber_task,
            payload,
            job_timeout=20 * 60,
            retry=Retry(max=3, interval=[10, 30, 60]))
        jobs.append({"chunk_index": idx, "job_id": job.id, "out_jsonl_key": out_jsonl_key})

    return {"doc_id": doc_id, "jobs": jobs, "total_jobs": len(jobs)}
