from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from redis import asyncio as redis

from ..config import settings

TTL_SECONDS = 60


class _LocalCache:
    def __init__(self) -> None:
        self._store: dict[int, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, org_id: int) -> Optional[str]:
        async with self._lock:
            entry = self._store.get(org_id)
            if not entry:
                return None
            value, expires_at = entry
            if expires_at < time.monotonic():
                self._store.pop(org_id, None)
                return None
            return value

    async def set(self, org_id: int, value: str, ttl: int) -> None:
        async with self._lock:
            self._store[org_id] = (value, time.monotonic() + ttl)

    async def invalidate(self, org_id: int) -> None:
        async with self._lock:
            self._store.pop(org_id, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


class SubscriptionCache:
    def __init__(self, ttl: int = TTL_SECONDS) -> None:
        self._ttl = ttl
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._local = _LocalCache()

    async def _client(self) -> Optional[redis.Redis]:
        if not settings.redis_url:
            return None
        async with self._redis_lock:
            if self._redis is None:
                self._redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            return self._redis

    async def get(self, org_id: int) -> Optional[dict[str, str]]:
        client = await self._client()
        key = f"subscription:{org_id}"
        if client:
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        raw = await self._local.get(org_id)
        return json.loads(raw) if raw else None

    async def set(self, org_id: int, payload: dict[str, str]) -> None:
        client = await self._client()
        key = f"subscription:{org_id}"
        data = json.dumps(payload)
        if client:
            await client.set(key, data, ex=self._ttl)
        else:
            await self._local.set(org_id, data, self._ttl)

    async def invalidate(self, org_id: int) -> None:
        client = await self._client()
        key = f"subscription:{org_id}"
        if client:
            await client.delete(key)
        await self._local.invalidate(org_id)

    async def clear(self) -> None:
        client = await self._client()
        if client:
            await client.flushdb()
        await self._local.clear()


subscription_cache = SubscriptionCache()
