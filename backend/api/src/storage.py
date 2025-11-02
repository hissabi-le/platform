from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from fastapi import HTTPException, status

from .config import settings


def _ensure_local_root() -> Path:
    root = Path(settings.storage_local_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _s3_client():
    if not settings.s3_bucket:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 bucket not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def _scan_bytes_with_clamav(data: bytes) -> None:
    host = settings.clamav_host
    if not host:
        return

    try:
        import clamd
    except ImportError as exc:  # pragma: no cover - configuration error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Antivirus unavailable") from exc

    try:
        client = clamd.ClamdNetworkSocket(host, settings.clamav_port)
        result = client.instream(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Antivirus service unavailable") from exc

    status_tuple = result.get("stream")
    if not status_tuple:
        return
    disposition, signature = status_tuple
    if disposition == "FOUND":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected: virus detected ({signature})",
        )


def store_file(org_id: int, filename: str, data: bytes, *, upload_id: Optional[int] = None) -> str:
    """Persist file data according to configured backend and return storage path."""
    _scan_bytes_with_clamav(data)

    unique_name = f"{uuid4().hex}_{os.path.basename(filename)}"
    if upload_id is not None:
        unique_name = f"{upload_id}_{unique_name}"

    if settings.storage_backend == "s3":
        client = _s3_client()
        key = f"{org_id}/{unique_name}"
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data)
        return f"s3://{settings.s3_bucket}/{key}"

    base = _ensure_local_root() / str(org_id)
    base.mkdir(parents=True, exist_ok=True)
    dest = base / unique_name
    dest.write_bytes(data)
    return str(dest)


def presign(storage_path: str, expires_seconds: int = 900) -> str:
    """Return a URL that can be used to download the stored file."""
    if storage_path.startswith("s3://"):
        if not settings.s3_bucket:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 not configured")
        _, bucket_and_key = storage_path.split("s3://", 1)
        bucket, key = bucket_and_key.split("/", 1)
        client = _s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    # Local storage paths are returned as-is for the caller to handle (dev mode)
    return storage_path


def load_file(storage_path: str) -> bytes:
    if storage_path.startswith("s3://"):
        if not settings.s3_bucket:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 not configured")
        _, bucket_and_key = storage_path.split("s3://", 1)
        bucket, key = bucket_and_key.split("/", 1)
        client = _s3_client()
        obj = client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    path = Path(storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
    return path.read_bytes()
