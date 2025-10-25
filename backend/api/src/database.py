# backend/api/src/database.py
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, Optional

from sqlalchemy import event, text
from sqlalchemy.engine import make_url, URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:secret@db:5432/postgres")
READ_DATABASE_URL = os.getenv("READ_DATABASE_URL")  # optional read replica

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # seconds; helps with LB/proxy idle closes
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))    # seconds to wait for a connection
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "60000"))  # 60s
DB_LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))             # 5s
DB_IDLE_TX_TIMEOUT_MS = int(os.getenv("DB_IDLE_TX_TIMEOUT_MS", "30000"))      # 30s
DB_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"

# ------------------------------------------------------------------
# Engine(s) & Session factories
# ------------------------------------------------------------------
def _create_engine(url: str):
    return create_async_engine(
        url,
        echo=DB_ECHO,
        future=True,
        pool_pre_ping=True,         # recover stale connections
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_recycle=DB_POOL_RECYCLE,
        pool_timeout=DB_POOL_TIMEOUT,
    )

engine = _create_engine(DATABASE_URL)
read_engine = _create_engine(READ_DATABASE_URL) if READ_DATABASE_URL else engine

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
async_read_session = async_sessionmaker(bind=read_engine, class_=AsyncSession, expire_on_commit=False)

# ------------------------------------------------------------------
# Declarative base (imported by models)
# ------------------------------------------------------------------
Base = declarative_base()

# ------------------------------------------------------------------
# Connection tuning per dialect
# ------------------------------------------------------------------
@event.listens_for(engine.sync_engine, "connect")
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
if read_engine is not engine:
    @event.listens_for(read_engine.sync_engine, "connect")
    def _on_connect_read(dbapi_conn, _):  # pragma: no cover
        _on_connect(dbapi_conn, _)

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
