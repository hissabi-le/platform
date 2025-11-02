from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from redis import asyncio as redis

from ..config import settings


class IdempotencyCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._local: dict[str, tuple[str, float]] = {}
        self._local_lock = asyncio.Lock()

    async def _client(self) -> Optional[redis.Redis]:
        if not settings.redis_url:
            return None
        async with self._redis_lock:
            if self._redis is None:
                self._redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            return self._redis

    async def get(self, key: str) -> Optional[dict]:
        client = await self._client()
        if client:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        async with self._local_lock:
            entry = self._local.get(key)
            if not entry:
                return None
            payload, expires_at = entry
            if expires_at < time.monotonic():
                self._local.pop(key, None)
                return None
            return json.loads(payload)

    async def set(self, key: str, payload: dict) -> None:
        client = await self._client()
        raw = json.dumps(payload)
        if client:
            await client.set(key, raw, ex=self._ttl)
        else:
            async with self._local_lock:
                self._local[key] = (raw, time.monotonic() + self._ttl)

    async def clear(self) -> None:
        client = await self._client()
        if client:
            await client.flushdb()
        async with self._local_lock:
            self._local.clear()


idempotency_cache = IdempotencyCache()
