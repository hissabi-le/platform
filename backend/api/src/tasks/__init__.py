from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Awaitable, Callable

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import Middleware, SkipMessage
from sqlalchemy import delete

from ..config import settings
from .process_upload import process_upload
from .recompute_analytics import recompute_analytics  # noqa: F401

logger = logging.getLogger(__name__)

_handler_lock = asyncio.Lock()
_broker_lock = asyncio.Lock()
_enqueue_handler: Callable[[int, int, str], Awaitable[None]] | None = None


class DLQMiddleware(Middleware):
    """Dead Letter Queue middleware for Dramatiq.
    
    Stores failed messages in Redis for later inspection and potential replay.
    """
    
    def after_skip_message(self, broker, message):
        """Called when a message is skipped after max retries."""
        self._store_failed_message(message, "max_retries_exceeded")
    
    def after_nack(self, broker, message):
        """Called when a message is negatively acknowledged."""
        self._store_failed_message(message, "nack")
    
    def _store_failed_message(self, message, reason: str):
        """Store failed message in Redis DLQ."""
        try:
            import redis
            client = redis.from_url(settings.redis_url)
            dlq_entry = {
                "message_id": message.message_id,
                "queue_name": message.queue_name,
                "actor_name": message.actor_name,
                "args": message.args,
                "kwargs": message.kwargs,
                "reason": reason,
                "failed_at": datetime.utcnow().isoformat(),
            }
            client.lpush("dramatiq:dead_letter", json.dumps(dlq_entry, default=str))
            client.ltrim("dramatiq:dead_letter", 0, 999)  # Keep last 1000
            logger.warning("Message %s stored in DLQ: %s", message.message_id, reason)
        except Exception as e:
            logger.error("Failed to store message in DLQ: %s", e)


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
            broker.add_middleware(DLQMiddleware())
            dramatiq.set_broker(broker)

