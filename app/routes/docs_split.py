import json
from uuid import uuid4

import fitz
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from rq import Retry

from app.services.rq_conn import get_queue
from app.services.storage import put_stream, put_bytes
from app.worker_tasks.docs_worker_tasks import split_pdf_chunk

router = APIRouter(prefix="/docs", tags=["Docs"])
MAX_BYTES = 50 * 1024 * 1024


def _count_pages_from_stream(fobj) -> int:
    pos = fobj.tell()
    data = fobj.read()
    fobj.seek(pos)
    doc = fitz.open(stream=data, filetype="pdf")
    return doc.page_count


@router.post("/upload-split/async")
async def upload_and_split_async(
        request: Request,
        file: UploadFile = File(...),
        pages_per_chunk: int = Form(default=25, ge=1, le=200),
):
    if (file.content_type or "").lower() not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Only PDF")

    # size
    size = None
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
    except:
        pass
    if size and size > MAX_BYTES: raise HTTPException(413, "Max 50MB")

    total_pages = _count_pages_from_stream(file.file)

    doc_id = uuid4().hex
    original_key = f"docs/{doc_id}/original.pdf"
    put_stream(original_key, file.file, length=size, content_type="application/pdf")

    ranges = []
    i = 1
    while i <= total_pages:
        start = i
        end = min(i + pages_per_chunk - 1, total_pages)
        ranges.append((start, end))
        i = end + 1

    manifest = {
        "doc_id": doc_id,
        "original": {"key": original_key, "size_bytes": size, "total_pages": total_pages},
        "pages_per_chunk": pages_per_chunk,
        "chunks": [],
        "status": "processing",
        "version": "1.0.0",
    }

    q = get_queue("docs")
    for idx, (start, end) in enumerate(ranges, start=1):
        chunk_key = f"docs/{doc_id}/chunks/chunk-{idx:04d}.pdf"
        meta_key = f"docs/{doc_id}/chunks/chunk-{idx:04d}.json"
        job = q.enqueue(
            split_pdf_chunk,
            original_key, doc_id, idx, start, end, chunk_key, meta_key,
            job_timeout=20 * 60, retry=Retry(max=3, interval=[10, 30, 60]),
        )
        manifest["chunks"].append({
            "index": idx, "start_page": start, "end_page": end,
            "expected_key": chunk_key, "meta_key": meta_key,
            "job_id": job.id, "status": "queued",
        })

    put_bytes(f"docs/{doc_id}/manifest.json",
              json.dumps(manifest, ensure_ascii=False, indent=2).encode(),
              content_type="application/json")

    return {
        "status": "queued", "doc_id": doc_id, "total_pages": total_pages,
        "pages_per_chunk": pages_per_chunk,
        "chunks": manifest["chunks"],
        "manifest": "docs/{}/manifest.json".format(doc_id),
    }
