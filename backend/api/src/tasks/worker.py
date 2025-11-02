from __future__ import annotations

import logging

import dramatiq
import dramatiq.cli
from dramatiq.brokers.redis import RedisBroker

from ..config import settings
from .process_upload import process_upload  # noqa: F401 ensure actor registration
from .recompute_analytics import recompute_analytics  # noqa: F401 ensure actor registration

logger = logging.getLogger(__name__)


def _init_broker() -> None:
    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)


def main() -> None:
    _init_broker()
    logger.info("Starting Dramatiq worker")
    dramatiq.cli.main()


if __name__ == "__main__":  # pragma: no cover
    main()
