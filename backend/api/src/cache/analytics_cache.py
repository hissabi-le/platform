from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from redis import asyncio as redis

from ..config import settings


class AnalyticsCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
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

    def _key(self, org_id: int, range_key: str) -> str:
        return f"analytics:pnl:{org_id}:{range_key}"

    async def get_pnl(self, org_id: int, range_key: str) -> Optional[dict]:
        key = self._key(org_id, range_key)
        client = await self._client()
        if client:
            data = await client.get(key)
            return json.loads(data) if data else None
        async with self._local_lock:
            entry = self._local.get(key)
            if not entry:
                return None
            payload, expires = entry
            if expires < time.monotonic():
                self._local.pop(key, None)
                return None
            return json.loads(payload)

    async def set_pnl(self, org_id: int, range_key: str, payload: dict) -> None:
        key = self._key(org_id, range_key)
        raw = json.dumps(payload)
        client = await self._client()
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

    async def clear_org(self, org_id: int) -> None:
        """Clear all cached analytics for a specific organization."""
        ranges = ["1m", "3m", "6m", "1y"]
        client = await self._client()
        for range_key in ranges:
            key = self._key(org_id, range_key)
            if client:
                await client.delete(key)
            async with self._local_lock:
                self._local.pop(key, None)


analytics_cache = AnalyticsCache()
