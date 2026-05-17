"""Revoked-JWT cache.

Stores revoked token ``jti`` values with TTL equal to the remaining lifetime of
the token. ``is_revoked`` returns ``True`` when a ``jti`` is in the cache.

Falls back to an in-process dict when ``REDIS_URL`` is unset (single-process
dev). Production must have Redis configured for revocation to be cluster-wide.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from redis import asyncio as redis

from ..config import settings


class TokenRevocationCache:
    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._local: dict[str, float] = {}
        self._local_lock = asyncio.Lock()

    async def _client(self) -> Optional[redis.Redis]:
        if not settings.redis_url:
            return None
        async with self._redis_lock:
            if self._redis is None:
                self._redis = redis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
            return self._redis

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        key = f"revoked:jti:{jti}"
        client = await self._client()
        if client is not None:
            await client.set(key, "1", ex=ttl_seconds)
            return
        async with self._local_lock:
            self._local[key] = time.monotonic() + ttl_seconds

    async def is_revoked(self, jti: str) -> bool:
        key = f"revoked:jti:{jti}"
        client = await self._client()
        if client is not None:
            return bool(await client.exists(key))
        async with self._local_lock:
            expires_at = self._local.get(key)
            if expires_at is None:
                return False
            if expires_at < time.monotonic():
                self._local.pop(key, None)
                return False
            return True


token_revocation_cache = TokenRevocationCache()
