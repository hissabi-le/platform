# backend/api/src/database.py
from __future__ import annotations
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, text
from sqlalchemy.engine import make_url

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:secret@db:5432/postgres")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "60000"))  # 60s

# ------------------------------------------------------------------
# Async engine & session factory (pooled, pre_ping, safe)
# ------------------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,           # kept from your version
    pool_pre_ping=True,    # recover stale connections
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
)

# PostgreSQL: set UTC + statement timeout on connect
@event.listens_for(engine.sync_engine, "connect")
def _on_connect(dbapi_conn, _):  # pragma: no cover (integration behavior)
    try:
        cur = dbapi_conn.cursor()
        # Safe on Postgres; ignored on others by except
        cur.execute("SET TIME ZONE 'UTC'")
        cur.execute(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT_MS}")
        cur.close()
    except Exception:
        # Non-Postgres dialects will land here; that's fine
        pass

# SQLite: enforce foreign key constraints (important for tests)
@event.listens_for(engine.sync_engine, "begin")
def _sqlite_fk_pragma(conn):  # pragma: no cover
    try:
        if conn.dialect.name == "sqlite":
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    except Exception:
        pass

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ------------------------------------------------------------------
# Declarative base (kept compatible with your current models)
# ------------------------------------------------------------------
Base = declarative_base()

# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session (your original name kept)."""
    async with async_session() as session:
        yield session

# ------------------------------------------------------------------
# Health & Alembic helpers
# ------------------------------------------------------------------
async def healthcheck() -> bool:
    """Simple DB ping for readiness probes."""
    try:
        async with async_session() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

def sync_database_url() -> str:
    """
    Return a synchronous SQLAlchemy URL for Alembic.
    - asyncpg -> psycopg
    - sqlite+aiosqlite -> sqlite
    """
    url = make_url(DATABASE_URL)
    if "+asyncpg" in url.drivername:
        url = url.set(drivername=url.drivername.replace("+asyncpg", "+psycopg"))
    if url.drivername == "sqlite+aiosqlite":
        url = url.set(drivername="sqlite")
    return str(url)
