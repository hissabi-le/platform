from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import delete

from ..config import settings

logger = logging.getLogger(__name__)

# CRITICAL: Set up the broker BEFORE importing any actors
# The @dramatiq.actor decorator registers actors with the current broker at import time
# If we import actors before setting the broker, they use the default (localhost:6379)
if settings.redis_url:
    _broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(_broker)
    logger.info("Dramatiq broker configured with Redis URL: %s", settings.redis_url)

# Now import actors - they will register with our configured broker
from .process_upload import process_upload  # noqa: E402
from .recompute_analytics import recompute_analytics  # noqa: F401, E402
from .whatsapp import process_whatsapp_message  # noqa: F401, E402


_handler_lock = asyncio.Lock()
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
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL must be set to enqueue upload tasks")
    process_upload.send(upload_id, org_id, storage_path)


async def enqueue_upload_processing(upload_id: int, org_id: int, storage_path: str) -> None:
    async with _handler_lock:
        handler = _enqueue_handler or _default_handler
    await handler(upload_id, org_id, storage_path)
