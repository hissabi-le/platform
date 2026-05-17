"""Per-org daily OpenAI token budget.

Prevents a single org (compromised account, runaway loop, abusive user) from
burning the OpenAI budget. Tracks total tokens consumed per org per UTC day;
when the cap is hit, ``check_or_raise`` raises 429.

The cap is best-effort and lossy: failures to update Redis are logged but
never block a request. Hard enforcement (refuse the API call) lives in
``check_or_raise``; bookkeeping happens in ``record_usage``.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
import redis as _sync_redis
from redis import asyncio as redis

from ..config import settings

log = logging.getLogger(__name__)

# Default: 1,000,000 tokens/org/day. ~50 chat-conversation-equivalents on
# gpt-4o-mini, or ~10 document ingestions on gpt-4o. Override per-env.
_DEFAULT_DAILY_TOKEN_CAP = 1_000_000


class SpendCapCache:
    def __init__(self, daily_token_cap: Optional[int] = None) -> None:
        self._cap = daily_token_cap or _DEFAULT_DAILY_TOKEN_CAP
        self._redis: Optional[redis.Redis] = None
        self._sync_redis: Optional[_sync_redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._local: dict[str, tuple[int, float]] = {}
        self._local_lock = asyncio.Lock()

    @property
    def daily_cap(self) -> int:
        return self._cap

    @staticmethod
    def _key(org_id: int) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"openai:spend:{org_id}:{today}"

    @staticmethod
    def _seconds_until_utc_midnight() -> int:
        now = datetime.now(timezone.utc)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # If we're past midnight already, advance one day.
        from datetime import timedelta

        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max(1, int((tomorrow - now).total_seconds()))

    async def _client(self) -> Optional[redis.Redis]:
        if not settings.redis_url:
            return None
        async with self._redis_lock:
            if self._redis is None:
                self._redis = redis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
            return self._redis

    async def get_usage(self, org_id: int) -> int:
        client = await self._client()
        key = self._key(org_id)
        if client is not None:
            raw = await client.get(key)
            return int(raw) if raw else 0
        async with self._local_lock:
            entry = self._local.get(key)
            if entry is None:
                return 0
            count, expires_at = entry
            if expires_at < time.monotonic():
                self._local.pop(key, None)
                return 0
            return count

    async def check_or_raise(self, org_id: int) -> None:
        """Raise 429 if the org is over the cap. Called before each OpenAI call."""
        usage = await self.get_usage(org_id)
        if usage >= self._cap:
            log.warning(
                "OpenAI daily token cap hit for org_id=%s (used=%s cap=%s)",
                org_id,
                usage,
                self._cap,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Daily AI usage limit reached for this organisation. "
                    "Resets at 00:00 UTC."
                ),
            )

    async def record_usage(self, org_id: int, tokens: int) -> None:
        """Increment usage. Failures are logged but never raised."""
        if tokens <= 0:
            return
        try:
            client = await self._client()
            key = self._key(org_id)
            ttl = self._seconds_until_utc_midnight()
            if client is not None:
                new_total = await client.incrby(key, tokens)
                # Set TTL only on first write of the day.
                if new_total == tokens:
                    await client.expire(key, ttl)
                return
            async with self._local_lock:
                current = self._local.get(key, (0, 0.0))
                new_count = current[0] + tokens
                self._local[key] = (new_count, time.monotonic() + ttl)
        except Exception:  # pragma: no cover - defensive
            log.exception("failed to record OpenAI usage for org_id=%s", org_id)

    # ----- sync API for Dramatiq workers ---------------------------------
    # Dramatiq actors are synchronous functions that internally drive an
    # asyncio loop via ``asyncio.run``. They cannot trivially await this
    # cache. The methods below give them a no-await path that uses the
    # synchronous redis client. If Redis is unavailable, they degrade to
    # the same in-process dict the async path uses.

    def _sync_client(self) -> Optional[_sync_redis.Redis]:
        if not settings.redis_url:
            return None
        if self._sync_redis is None:
            self._sync_redis = _sync_redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._sync_redis

    def get_usage_sync(self, org_id: int) -> int:
        try:
            client = self._sync_client()
            key = self._key(org_id)
            if client is not None:
                raw = client.get(key)
                return int(raw) if raw else 0
            entry = self._local.get(key)
            if entry is None:
                return 0
            count, expires_at = entry
            if expires_at < time.monotonic():
                self._local.pop(key, None)
                return 0
            return count
        except Exception:  # pragma: no cover - defensive
            log.exception("get_usage_sync failed")
            return 0

    def is_over_cap_sync(self, org_id: int) -> bool:
        return self.get_usage_sync(org_id) >= self._cap

    def record_usage_sync(self, org_id: int, tokens: int) -> None:
        """Worker-side increment. Same semantics as ``record_usage``."""
        if tokens <= 0:
            return
        try:
            client = self._sync_client()
            key = self._key(org_id)
            ttl = self._seconds_until_utc_midnight()
            if client is not None:
                new_total = client.incrby(key, tokens)
                if new_total == tokens:
                    client.expire(key, ttl)
                return
            current = self._local.get(key, (0, 0.0))
            self._local[key] = (current[0] + tokens, time.monotonic() + ttl)
        except Exception:  # pragma: no cover - defensive
            log.exception("record_usage_sync failed for org_id=%s", org_id)


spend_cap_cache = SpendCapCache()
