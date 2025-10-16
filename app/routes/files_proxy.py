import mimetypes
import os
import re
from typing import Optional, Iterator
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Header, Response
from fastapi.responses import StreamingResponse

from app.services.storage import get_minio_client, BUCKET

router = APIRouter(prefix="/files", tags=["files"])

SAFE_KEY_RE = re.compile(r"^[a-zA-Z0-9/_\.\-]+$")  # simple allowlist


def _iter_minio(resp, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    try:
        while True:
            data = resp.read(chunk_size)
            if not data:
                break
            yield data
    finally:
        try:
            resp.close()
            resp.release_conn()
        except Exception:
            pass


def _sanitize_key(raw: str) -> str:
    key = unquote(raw).lstrip("/")
    # basic traversal guard
    if ".." in key or not SAFE_KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="invalid key")
    return key


@router.get("/proxy")
def proxy_file(
        key: str = Query(..., description="Object key in BUCKET"),
        disposition: str = Query("inline", pattern="^(inline|attachment)$"),
        filename: Optional[str] = Query(None, description="Override download filename"),
        range_header: Optional[str] = Header(None, alias="Range"),
):
    """
    Stream file from MinIO via API gateway.
    Supports basic 'Range: bytes=start-end' for partial content.
    """
    client = get_minio_client()
    key = _sanitize_key(key)

    # stat object for metadata
    try:
        stat = client.stat_object(BUCKET, key)
    except Exception:
        raise HTTPException(status_code=404, detail="object not found")

    content_type = stat.content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    total_size = stat.size

    # filename for Content-Disposition
    fname = filename or os.path.basename(key) or "file"
    cd = f'{disposition}; filename="{fname}"'

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": cd,
        "Cache-Control": "private, max-age=0, no-store",
        "ETag": stat.etag or "",
        "Last-Modified": stat.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT") if stat.last_modified else "",
    }

    offset = None
    length = None
    status_code = 200

    # Parse simple Range: bytes=start-end
    if range_header:
        m = re.match(r"bytes=(\d*)-(\d*)", range_header.replace(" ", ""))
        if m:
            start_str, end_str = m.groups()
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else total_size - 1
            if start > end or start >= total_size:
                # Invalid range
                return Response(
                    status_code=416,
                    headers={
                        **headers,
                        "Content-Range": f"bytes */{total_size}",
                    },
                )
            offset = start
            length = end - start + 1
            status_code = 206  # Partial Content
            headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
            headers["Content-Length"] = str(length)
        else:
            # Bad range format
            raise HTTPException(status_code=400, detail="invalid Range header")

    try:
        if offset is not None and length is not None:
            resp = client.get_object(BUCKET, key, offset=offset, length=length)
        else:
            resp = client.get_object(BUCKET, key)
            headers["Content-Length"] = str(total_size)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"minio get_object error: {e}")

    return StreamingResponse(
        _iter_minio(resp),
        media_type=content_type,
        status_code=status_code,
        headers=headers,
    )
