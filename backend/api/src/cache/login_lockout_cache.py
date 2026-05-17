"""Per-account failed-login counter and lockout.

The IP-based rate limiter caps password-spraying from one source, but doesn't
defend a single account from a distributed attack. This cache tracks failed
attempts per email and locks the account for a cooling-off period after N
consecutive failures.

Falls back to an in-process dict if Redis isn't configured (single-process
dev only — production must run with Redis for cluster-wide enforcement).
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from redis import asyncio as redis

from ..config import settings


class LoginLockoutCache:
    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 900) -> None:
        # Defaults: 5 failures -> 15 min lockout (NIST 800-63B compatible).
        self._max = max_attempts
        self._lockout = lockout_seconds
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._local_count: dict[str, int] = {}
        self._local_lock_until: dict[str, float] = {}
        self._local_lock = asyncio.Lock()

    @property
    def max_attempts(self) -> int:
        return self._max

    @property
    def lockout_seconds(self) -> int:
        return self._lockout

    @staticmethod
    def _key(email: str) -> str:
        return f"login:fail:{email.strip().lower()}"

    @staticmethod
    def _locked_key(email: str) -> str:
        return f"login:locked:{email.strip().lower()}"

    async def _client(self) -> Optional[redis.Redis]:
        if not settings.redis_url:
            return None
        async with self._redis_lock:
            if self._redis is None:
                self._redis = redis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
            return self._redis

    async def is_locked(self, email: str) -> bool:
        client = await self._client()
        if client is not None:
            return bool(await client.exists(self._locked_key(email)))
        async with self._local_lock:
            expires_at = self._local_lock_until.get(self._locked_key(email))
            if expires_at is None:
                return False
            if expires_at < time.monotonic():
                self._local_lock_until.pop(self._locked_key(email), None)
                return False
            return True

    async def record_failure(self, email: str) -> bool:
        """Increment the failure counter. Returns True if the account is now locked."""
        client = await self._client()
        if client is not None:
            key = self._key(email)
            new_count = await client.incr(key)
            if new_count == 1:
                # Roll the failure window with the lockout TTL so old counters
                # don't accumulate forever.
                await client.expire(key, self._lockout)
            if new_count >= self._max:
                await client.set(self._locked_key(email), "1", ex=self._lockout)
                await client.delete(key)
                return True
            return False
        async with self._local_lock:
            count = self._local_count.get(self._key(email), 0) + 1
            if count >= self._max:
                self._local_lock_until[self._locked_key(email)] = (
                    time.monotonic() + self._lockout
                )
                self._local_count.pop(self._key(email), None)
                return True
            self._local_count[self._key(email)] = count
            return False

    async def clear(self, email: str) -> None:
        """Wipe the counter and any lock — call on successful login."""
        client = await self._client()
        if client is not None:
            await client.delete(self._key(email), self._locked_key(email))
            return
        async with self._local_lock:
            self._local_count.pop(self._key(email), None)
            self._local_lock_until.pop(self._locked_key(email), None)


login_lockout_cache = LoginLockoutCache()
