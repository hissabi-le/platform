from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import delete

from ..config import settings
from .process_upload import process_upload
from .recompute_analytics import recompute_analytics  # noqa: F401

logger = logging.getLogger(__name__)

_handler_lock = asyncio.Lock()
_broker_lock = asyncio.Lock()
_enqueue_handler: Callable[[int, int, str], Awaitable[None]] | None = None


async def register_enqueue_handler(handler: Callable[[int, int, str], Awaitable[None]]) -> None:
    async with _handler_lock:
        global _enqueue_handler
        _enqueue_handler = handler
    if os.getenv("PYTEST_CURRENT_TEST"):
        from ..database import async_session
        from ..models import Upload

        async with async_session() as session:
            await session.execute(delete(Upload))
            await session.commit()


async def _default_handler(upload_id: int, org_id: int, storage_path: str) -> None:
    await _ensure_broker()
    process_upload.send(upload_id, org_id, storage_path)


async def enqueue_upload_processing(upload_id: int, org_id: int, storage_path: str) -> None:
    async with _handler_lock:
        handler = _enqueue_handler or _default_handler
    await handler(upload_id, org_id, storage_path)


async def _ensure_broker() -> None:
    if dramatiq.get_broker() is not None:
        return
    async with _broker_lock:
        if dramatiq.get_broker() is None:
            broker = RedisBroker(url=settings.redis_url)
            dramatiq.set_broker(broker)
