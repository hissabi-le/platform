# backend/api/src/database.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Optional

from sqlalchemy import event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool, NullPool

from .config import settings

# ... (omitted)

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
DATABASE_URL = settings.database_url
READ_DATABASE_URL = settings.read_database_url

DB_POOL_SIZE = settings.db_pool_size
DB_MAX_OVERFLOW = settings.db_max_overflow
DB_POOL_RECYCLE = settings.db_pool_recycle  # seconds; helps with LB/proxy idle closes
DB_POOL_TIMEOUT = settings.db_pool_timeout    # seconds to wait for a connection
DB_STATEMENT_TIMEOUT_MS = settings.db_statement_timeout_ms  # 60s
DB_LOCK_TIMEOUT_MS = settings.db_lock_timeout_ms             # 5s
DB_IDLE_TX_TIMEOUT_MS = settings.db_idle_tx_timeout_ms      # 30s
DB_ECHO = settings.sqlalchemy_echo

# ------------------------------------------------------------------
# Engine(s) & Session factories
# ------------------------------------------------------------------
def _create_engine(url: str):
    url_obj = make_url(url)

    kwargs: dict = {
        "echo": DB_ECHO,
        "future": True,
    }

    if url_obj.drivername.startswith("sqlite"):
        kwargs.update(
            {
                "pool_pre_ping": False,
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            }
        )
    else:
        # Use NullPool to prevent connection sharing issues across Gunicorn workers
        kwargs.update(
            {
                "pool_pre_ping": True,
                "poolclass": NullPool,
            }
        )

    return create_async_engine(url, **kwargs)

engine = _create_engine(DATABASE_URL)
read_engine = _create_engine(READ_DATABASE_URL) if READ_DATABASE_URL else engine

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
async_read_session = async_sessionmaker(bind=read_engine, class_=AsyncSession, expire_on_commit=False)

# ------------------------------------------------------------------
# Declarative base (imported by models)
# ------------------------------------------------------------------
Base = declarative_base()

if settings.database_url.startswith("sqlite+aiosqlite:///:memory:"):
    _orig_create_all = Base.metadata.create_all

    def _create_all_with_reset(bind=None, *args, **kwargs):
        actual_bind = bind or kwargs.get("bind")
        if actual_bind is None:
            actual_bind = engine.sync_engine
        Base.metadata.drop_all(bind=actual_bind)
        return _orig_create_all(bind=actual_bind, *args, **kwargs)

    Base.metadata.create_all = _create_all_with_reset  # type: ignore[assignment]

# ------------------------------------------------------------------
# Connection tuning per dialect
# ------------------------------------------------------------------
# @event.listens_for(engine.sync_engine, "connect")
def _on_connect(dbapi_conn, _):  # pragma: no cover (integration behavior)
    try:
        cur = dbapi_conn.cursor()
        try:
            # Postgres-specific session parameters (ignored by others)
            cur.execute("SET TIME ZONE 'UTC'")
            cur.execute(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT_MS}")
            cur.execute(f"SET lock_timeout = {DB_LOCK_TIMEOUT_MS}")
            cur.execute(f"SET idle_in_transaction_session_timeout = {DB_IDLE_TX_TIMEOUT_MS}")
            cur.execute("SET client_encoding = 'UTF8'")
        except Exception:
            # Not Postgres (e.g., SQLite) → ignore
            pass
        try:
            # SQLite test env hardening / performance
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("PRAGMA journal_mode = WAL")
            cur.execute("PRAGMA synchronous = NORMAL")
        except Exception:
            # Not SQLite or unsupported → ignore
            pass
        cur.close()
    except Exception:
        # Keep connection usable even if tuning fails
        pass

# Apply same tuning for read engine if distinct
# if read_engine is not engine:
#     @event.listens_for(read_engine.sync_engine, "connect")
#     def _on_connect_read(dbapi_conn, _):  # pragma: no cover
#         _on_connect(dbapi_conn, _)

# ------------------------------------------------------------------
# FastAPI dependencies
# ------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Primary (write-capable) session."""
    async with async_session() as session:
        yield session

async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session (uses read replica if configured)."""
    async with async_read_session() as session:
        yield session

# Optional convenience for atomic units of work where suitable.
@asynccontextmanager
async def db_transaction(write: bool = True) -> AsyncIterator[AsyncSession]:
    """Yield a session and auto-commit/rollback around the block."""
    factory = async_session if write else async_read_session
    async with factory() as session:
        try:
            yield session
            if write:
                await session.commit()
        except Exception:
            if write:
                await session.rollback()
            raise

# ------------------------------------------------------------------
# Health & Alembic helpers
# ------------------------------------------------------------------
async def healthcheck() -> bool:
    """Simple DB ping for readiness probes."""
    try:
        async with async_read_session() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

def _coerce_sync_driver(url: URL) -> URL:
    """Convert async drivers to sync equivalents for Alembic."""
    drv = url.drivername
    if "+asyncpg" in drv:
        url = url.set(drivername=drv.replace("+asyncpg", "+psycopg"))
    if drv == "sqlite+aiosqlite":
        url = url.set(drivername="sqlite")
    return url

def sync_database_url() -> str:
    """
    Return a synchronous SQLAlchemy URL string for Alembic from DATABASE_URL.
    - postgresql+asyncpg -> postgresql+psycopg
    - sqlite+aiosqlite  -> sqlite
    """
    url = make_url(DATABASE_URL)
    return str(_coerce_sync_driver(url))
