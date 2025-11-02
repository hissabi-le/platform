from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from .config import settings


class RateLimitExceeded(Exception):
    """Raised when a rate limit token bucket is exhausted."""


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str) -> None:
        now = time.monotonic()
        async with self._lock:
            bucket = self._calls[key]
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                raise RateLimitExceeded
            bucket.append(now)

    async def reset(self) -> None:
        async with self._lock:
            self._calls.clear()


login_rate_limiter = SlidingWindowLimiter(settings.rate_limit_login_per_min, 60.0)
uploads_rate_limiter = SlidingWindowLimiter(settings.rate_limit_uploads_per_min, 60.0)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


async def enforce_login_rate_limit(request: Request) -> None:
    try:
        login_rate_limiter.max_calls = max(
            1, _env_int("RATE_LIMIT_LOGIN_PER_MIN", settings.rate_limit_login_per_min)
        )
        await login_rate_limiter.hit(_client_key(request))
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again shortly.",
        ) from None


async def enforce_upload_rate_limit(request: Request) -> None:
    try:
        uploads_rate_limiter.max_calls = max(
            1, _env_int("RATE_LIMIT_UPLOADS_PER_MIN", settings.rate_limit_uploads_per_min)
        )
        await uploads_rate_limiter.hit(_client_key(request))
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many uploads. Please slow down.",
        ) from None
