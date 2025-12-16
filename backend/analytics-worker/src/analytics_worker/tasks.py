from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Sequence

from celery import Celery, group

from .config import settings
from .db import session_scope
from .logging import configure_logging
from .repositories.organisations import iter_org_ids
from .services.analytics import run_job

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

celery_app = Celery(settings.app_name, broker=settings.broker_url, backend=settings.result_backend)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    worker_prefetch_multiplier=settings.worker_prefetch_multiplier,
    worker_max_tasks_per_child=500,
    broker_connection_retry_on_startup=True,
)


async def _refresh(org_id: int, ranges: Sequence[str] | None, reason: str | None):
    async with session_scope() as session:
        return await run_job(session, org_id, ranges=ranges, reason=reason)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def refresh_org_analytics(self, org_id: int, ranges: Sequence[str] | None = None, reason: str | None = None):
    """
    Refresh cached analytics for a single organisation.
    """
    logger.info("Refreshing analytics for org=%s ranges=%s reason=%s", org_id, ranges, reason)
    return asyncio.run(_refresh(org_id, ranges, reason))


@celery_app.task(bind=True)
def refresh_all_orgs(self, ranges: Sequence[str] | None = None, reason: str | None = None):
    """
    Fan out refresh jobs for every organisation. Returns the celery group result id.
    """
    logger.info("Enqueue refresh for all organisations (reason=%s)", reason)

    async def _fanout():
        async with session_scope() as session:
            batches = []
            async for ids in iter_org_ids(session):
                batches.extend(ids)
            return batches

    org_ids = asyncio.run(_fanout())
    if not org_ids:
        logger.info("No organisations found for refresh")
        return None
    tasks = group(refresh_org_analytics.s(org_id, ranges=ranges, reason=reason) for org_id in org_ids)
    result = tasks.apply_async()
    logger.info("Dispatched %s refresh jobs (group id=%s)", len(org_ids), result.id)
    return result.id


@celery_app.task
def worker_healthcheck():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


__all__ = ["celery_app", "refresh_org_analytics", "refresh_all_orgs"]
