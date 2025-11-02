import os
import tempfile
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from src import storage
from src.config import settings


@contextmanager
def override_setting(name: str, value):
    original = getattr(settings, name)
    setattr(settings, name, value)
    try:
        yield
    finally:
        setattr(settings, name, original)


def test_store_file_local(tmp_path):
    with override_setting("storage_backend", "local"), override_setting("storage_local_root", str(tmp_path)):
        path = storage.store_file(org_id=1, filename="test.txt", data=b"hello world")
        assert path.startswith(str(tmp_path))
        assert os.path.exists(path)
        url = storage.presign(path)
        assert url == path


def test_store_file_s3(monkeypatch):
    class StubClient:
        def __init__(self):
            self.uploads = []

        def put_object(self, Bucket, Key, Body):
            self.uploads.append((Bucket, Key, Body))

        def generate_presigned_url(self, operation_name, Params, ExpiresIn):
            assert operation_name == "get_object"
            return f"https://example.com/{Params['Key']}?exp={ExpiresIn}"

    client = StubClient()

    def _stub_client():
        return client

    with (
        override_setting("storage_backend", "s3"),
        override_setting("s3_bucket", "test-bucket"),
        override_setting("s3_access_key_id", "key"),
        override_setting("s3_secret_access_key", "secret"),
    ):
        monkeypatch.setattr(storage, "_s3_client", _stub_client)
        path = storage.store_file(org_id=2, filename="report.csv", data=b"abc")
        assert path.startswith("s3://test-bucket/")
        assert client.uploads

        presigned = storage.presign(path, expires_seconds=60)
        assert presigned.startswith("https://example.com")


def test_antivirus_detection(monkeypatch):
    def fake_scan(data: bytes) -> None:
        raise HTTPException(status_code=400, detail="virus")

    monkeypatch.setattr(storage, "_scan_bytes_with_clamav", fake_scan)
    with pytest.raises(HTTPException) as exc:
        storage.store_file(org_id=1, filename="evil.xls", data=b"malware")
    assert exc.value.status_code == 400
