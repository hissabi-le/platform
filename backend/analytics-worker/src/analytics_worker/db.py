from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .config import settings


def _engine_kwargs(url: str) -> dict:
    url_obj = make_url(url)
    kwargs: dict = {"echo": settings.sqlalchemy_echo, "future": True}
    if url_obj.drivername.startswith("sqlite"):
        kwargs.update(
            {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            }
        )
    else:
        kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_timeout": settings.db_pool_timeout,
                "pool_recycle": settings.db_pool_recycle,
            }
        )
    return kwargs


engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping() -> bool:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _on_connect(dbapi_conn, _):  # pragma: no cover - integration behavior only
    try:
        cur = dbapi_conn.cursor()
        cur.execute("SET TIME ZONE 'UTC'")
        cur.execute(f"SET statement_timeout = {settings.db_pool_timeout * 1000}")
        cur.close()
    except Exception:
        # non-Postgres backends or tuning failure → ignore
        return


event.listen(engine.sync_engine, "connect", _on_connect)


__all__ = ["async_session", "session_scope", "engine", "ping"]
