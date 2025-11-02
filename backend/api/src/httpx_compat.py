from __future__ import annotations

import inspect
from functools import wraps
from typing import Any


def ensure_async_client_app_support() -> None:
    """
    httpx>=0.28 removed the `app` parameter from AsyncClient.
    Re-inject support so our tests (and legacy call sites) continue to work.
    """
    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx optional
        return

    AsyncClient = getattr(httpx, "AsyncClient", None)
    ASGITransport = getattr(httpx, "ASGITransport", None)
    if AsyncClient is None or ASGITransport is None:
        return

    params = inspect.signature(AsyncClient.__init__).parameters
    if "app" in params:
        return  # Already supports legacy signature

    original_init = AsyncClient.__init__

    @wraps(original_init)
    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        app = kwargs.pop("app", None)
        transport = kwargs.get("transport")
        if app is not None and transport is None:
            kwargs["transport"] = ASGITransport(app=app)
        return original_init(self, *args, **kwargs)

    AsyncClient.__init__ = patched_init
