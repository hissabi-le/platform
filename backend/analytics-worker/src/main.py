from __future__ import annotations

import os

from analytics_worker.config import settings
from analytics_worker.logging import configure_logging
from analytics_worker.tasks import celery_app

# Initialize Sentry for error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[CeleryIntegration()],
            traces_sample_rate=0.1,
        )
except ImportError:
    pass  # sentry-sdk not installed


def main() -> None:
    configure_logging(settings.log_level)
    concurrency = int(os.getenv("WORKER_CONCURRENCY") or settings.worker_concurrency)
    argv = [
        "worker",
        f"--loglevel={settings.log_level.lower()}",
        f"--concurrency={concurrency}",
        f"--prefetch-multiplier={settings.worker_prefetch_multiplier}",
    ]
    if os.getenv("WORKER_WITH_BEAT", "").lower() in {"1", "true", "yes"}:
        argv.append("--beat")
    celery_app.worker_main(argv)


if __name__ == "__main__":  # pragma: no cover
    main()

