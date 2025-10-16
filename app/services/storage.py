import io
import json
import os

from minio import Minio
from minio.error import S3Error

_client = None
BUCKET = os.getenv("MINIO_BUCKET", "vdr-extract")


def get_minio_client():
    """
    Initialize MinIO client with automatic bucket creation.
    """
    global _client
    if _client:
        return _client

    _client = Minio(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minio"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minio123"),
        secure=False,
    )

    # ✅ Ensure bucket exists
    try:
        if not _client.bucket_exists(BUCKET):
            _client.make_bucket(BUCKET)
            print(f"✅ Created bucket: {BUCKET}")
        else:
            print(f"ℹ️ Bucket '{BUCKET}' already exists")
    except S3Error as e:
        print(f"⚠️ Error checking/creating bucket '{BUCKET}': {e}")

    return _client


def put_bytes(key: str, b: bytes, content_type: str = "application/octet-stream"):
    c = get_minio_client()
    c.put_object(BUCKET, key, io.BytesIO(b), len(b), content_type=content_type)


def put_stream(key: str, fileobj, length: int | None, content_type: str):
    c = get_minio_client()
    if length is None:
        c.put_object(BUCKET, key, fileobj, -1, part_size=5 * 1024 * 1024, content_type=content_type)
    else:
        c.put_object(BUCKET, key, fileobj, length, content_type=content_type)


def get_json_from_minio(client: Minio, bucket: str, key: str):
    try:
        resp = client.get_object(bucket, key)
        data = resp.read()
        resp.close()
        resp.release_conn()
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None
