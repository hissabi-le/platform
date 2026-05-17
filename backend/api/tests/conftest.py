import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

try:
    from fastapi.testclient import TestClient
    from src.main import app
    from src.database import engine, Base
except Exception as exc:  # pragma: no cover - handled via skip
    pytest.skip(f"Required dependencies not installed: {exc}", allow_module_level=True)


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> None:
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())


@pytest.fixture(autouse=True)
def _reset_global_state() -> None:
    """Reset module-level caches between tests to prevent state leakage."""
    from src.cache.login_lockout_cache import login_lockout_cache
    from src.cache.subscription_cache import subscription_cache
    from src.cache.token_revocation_cache import token_revocation_cache
    from src.rate_limit import login_rate_limiter, uploads_rate_limiter

    asyncio.run(subscription_cache.clear())
    asyncio.run(login_rate_limiter.reset())
    asyncio.run(uploads_rate_limiter.reset())
    # Drop local in-process caches that have no public ``clear`` method.
    token_revocation_cache._local.clear()
    login_lockout_cache._local_count.clear()
    login_lockout_cache._local_lock_until.clear()


@pytest_asyncio.fixture
async def async_db_session():
    """Provide an async database session for testing."""
    from src.database import async_session
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
