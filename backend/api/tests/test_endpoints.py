# File: tests/test_endpoints.py
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

try:
    from httpx import AsyncClient
    from src.main import app
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)

@pytest.mark.asyncio
async def test_healthz():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_version():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data and isinstance(data["version"], str)

@pytest.mark.asyncio
async def test_list_documents_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/documents")
    assert r.status_code == 401
