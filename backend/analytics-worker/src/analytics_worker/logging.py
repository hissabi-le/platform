from __future__ import annotations

import logging
import os
import sys
from typing import Any

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str | int | None = None) -> None:
    """
    Configure root logging only once. Celery forks processes so prefer simple stdio setup.
    """
    if getattr(configure_logging, "_configured", False):
        return
    log_level = _resolve_level(level)
    logging.basicConfig(level=log_level, format=LOG_FORMAT, stream=sys.stdout)
    logging.getLogger("celery").setLevel(log_level)
    logging.getLogger("kombu").setLevel(log_level)
    configure_logging._configured = True  # type: ignore[attr-defined]


def _resolve_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        return getattr(logging, env_level.upper(), logging.INFO)
    return logging.INFO


__all__ = ["configure_logging"]
