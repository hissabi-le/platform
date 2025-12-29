from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4

from redis import asyncio as aioredis

from .config import settings

logger = logging.getLogger(__name__)


class _RedisClient:
    _client: aioredis.Redis | None = None
    _lock = asyncio.Lock()

    async def get(self) -> aioredis.Redis | None:
        if not settings.redis_url:
            return None
        if self._client:
            return self._client
        async with self._lock:
            if not self._client:
                self._client = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    health_check_interval=30,
                )
        return self._client


redis_client = _RedisClient()


class AnalyticsCache:
    """
    Distributed analytics cache backed by Redis.
    
    Note: Unlike previous versions, this cache does NOT have a local fallback.
    In distributed environments (Kubernetes), local caching creates "split-brain"
    data where different pods see different data. When Redis is unavailable,
    this cache returns None to force recomputation (slower but correct).
    """
    
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds

    def _key(self, org_id: int, range_key: str) -> str:
        return f"analytics:pnl:{org_id}:{range_key}"

    async def get(self, org_id: int, range_key: str) -> Optional[dict[str, Any]]:
        key = self._key(org_id, range_key)
        client = await redis_client.get()
        if client:
            try:
                payload = await client.get(key)
                if payload:
                    return json.loads(payload)
            except Exception as e:
                logger.warning("Redis get failed for %s: %s", key, e)
        else:
            logger.warning("Redis unavailable, cache miss for %s", key)
        return None

    async def set(self, org_id: int, range_key: str, payload: dict[str, Any]) -> None:
        key = self._key(org_id, range_key)
        raw = json.dumps(payload, default=str)
        client = await redis_client.get()
        if client:
            try:
                await client.set(key, raw, ex=self._ttl)
            except Exception as e:
                logger.warning("Redis set failed for %s: %s", key, e)
        else:
            logger.warning("Redis unavailable, cannot cache %s", key)


class JobStore:
    def __init__(self, ttl_seconds: int = settings.analytics_job_ttl_seconds) -> None:
        self._ttl = ttl_seconds

    def _key(self, job_id: str) -> str:
        return f"analytics:jobs:{job_id}"

    async def start(self, job_id: str, payload: Dict[str, Any]) -> None:
        client = await redis_client.get()
        if not client:
            return
        data = json.dumps({"status": "running", **payload})
        await client.set(self._key(job_id), data, ex=self._ttl)

    async def complete(self, job_id: str, payload: Dict[str, Any]) -> None:
        client = await redis_client.get()
        if not client:
            return
        data = json.dumps({"status": "succeeded", **payload})
        await client.set(self._key(job_id), data, ex=self._ttl)

    async def fail(self, job_id: str, payload: Dict[str, Any]) -> None:
        client = await redis_client.get()
        if not client:
            return
        data = json.dumps({"status": "failed", **payload})
        await client.set(self._key(job_id), data, ex=self._ttl)


class DistributedLock:
    def __init__(self, name: str, ttl_seconds: int = 300) -> None:
        self._name = f"analytics:lock:{name}"
        self._ttl = ttl_seconds
        self._token = str(uuid4())

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[bool]:
        client = await redis_client.get()
        if not client:
            yield True  # fallback to no lock when redis unavailable
            return
        locked = await client.set(self._name, self._token, ex=self._ttl, nx=True)
        try:
            yield bool(locked)
        finally:
            if locked:
                try:
                    script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    end
                    return 0
                    """
                    await client.eval(script, 1, self._name, self._token)
                except Exception:
                    logger.warning("Failed to release lock %s", self._name, exc_info=True)


analytics_cache = AnalyticsCache(settings.analytics_cache_ttl_seconds)
job_store = JobStore()


__all__ = ["analytics_cache", "job_store", "DistributedLock", "redis_client"]
