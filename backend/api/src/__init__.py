"""Platform API package."""
"""
Hissabi backend package initializer.

- Exposes package version via ``__version__``
- Idempotent runtime hardening on import:
  - Forces UTC timezone (configurable)
  - Sets Decimal context (precision & rounding)
  - Configures logging if no handlers exist (plain or JSON)
- Provides ``init_runtime()`` if you want to re-run setup explicitly.
"""

import logging
import os
import sys
from decimal import getcontext, ROUND_HALF_UP
from contextlib import suppress

__all__ = ["__version__", "init_runtime", "get_logger"]

# Semver for the backend package; can be overridden by env
__version__ = os.getenv("HISSABI_VERSION", "0.2.0")


def init_runtime() -> None:
    """Configure safe defaults for prod & tests. Idempotent."""
    # ---- Timezone (UTC) ----
    if os.getenv("HISSABI_FORCE_UTC", "1") in {"1", "true", "True"}:
        with suppress(Exception):
            os.environ["TZ"] = "UTC"
            import time
            if hasattr(time, "tzset"):
                time.tzset()

    # ---- Decimal context ----
    ctx = getcontext()
    try:
        ctx.prec = int(os.getenv("HISSABI_DECIMAL_PREC", "28"))
    except Exception:
        ctx.prec = 28
    ctx.rounding = ROUND_HALF_UP

    # ---- Logging ----
    root = logging.getLogger()
    if not root.handlers:  # don't clobber uvicorn/gunicorn handlers
        level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        fmt = os.getenv("HISSABI_LOG_FORMAT", "plain").lower()
        if fmt == "json":
            class JsonFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
                    import json, time
                    payload = {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                        "level": record.levelname,
                        "name": record.name,
                        "msg": record.getMessage(),
                    }
                    if record.exc_info:
                        payload["exc_info"] = self.formatException(record.exc_info)
                    return json.dumps(payload, ensure_ascii=False)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setFormatter(JsonFormatter())
            root.addHandler(handler)
            root.setLevel(level)
        else:
            logging.basicConfig(
                level=level,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            )

    # Quiet down noisy libs by default
    for noisy in ("sqlalchemy.engine", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(os.getenv("NOISY_LOG_LEVEL", "WARNING"))


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger with a NullHandler if logging isn't configured."""
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


# Auto-run on import (safe/idempotent) so CLI/test users get sane defaults
init_runtime()
