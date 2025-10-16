import io
import json
from datetime import datetime

import fitz

from app.services.storage import get_minio_client, BUCKET


def _get_bytes(key: str) -> bytes:
    c = get_minio_client()
    obj = c.get_object(BUCKET, key)
    try:
        return obj.read()
    finally:
        obj.close();
        obj.release_conn()


def _put_bytes(key: str, b: bytes, ctype: str):
    c = get_minio_client()
    c.put_object(BUCKET, key, io.BytesIO(b), len(b), content_type=ctype)


def split_pdf_chunk(original_key: str, doc_id: str, chunk_index: int,
                    start_page: int, end_page: int, out_key: str, meta_key: str):
    raw = _get_bytes(original_key)
    try:
        src = fitz.open(stream=raw, filetype="pdf")
    except Exception as e:
        meta = {"doc_id": doc_id, "chunk_index": chunk_index, "status": "error", "error": str(e)}
        _put_bytes(meta_key, json.dumps(meta).encode(), "application/json")
        return meta

    total = src.page_count
    s = max(1, min(start_page, total));
    e = max(1, min(end_page, total))
    if s > e: s, e = e, s
    dst = fitz.open()
    for pno in range(s - 1, e):
        dst.insert_pdf(src, from_page=pno, to_page=pno)
    buf = dst.write()
    dst.close();
    src.close()

    _put_bytes(out_key, buf, "application/pdf")
    meta = {
        "doc_id": doc_id, "chunk_index": chunk_index, "start_page": s, "end_page": e,
        "out_key": out_key, "size_bytes": len(buf), "num_pages": e - s + 1,
        "status": "done", "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    _put_bytes(meta_key, json.dumps(meta, ensure_ascii=False, indent=2).encode(), "application/json")
    return meta
