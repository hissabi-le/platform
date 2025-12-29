"""Prometheus metrics for analytics worker.

This module provides instrumentation for analytics job processing,
enabling monitoring of job duration, success/failure rates, and throughput.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# Try to import prometheus_client, but make it optional
try:
    from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

if _HAS_PROMETHEUS:
    # Create a registry
    REGISTRY = CollectorRegistry()

    # Job metrics
    JOB_DURATION = Histogram(
        'analytics_job_duration_seconds',
        'Time spent processing analytics jobs',
        ['org_id', 'range_key'],
        registry=REGISTRY,
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
    )

    JOB_FAILURE = Counter(
        'analytics_job_failure_total',
        'Total number of failed analytics jobs',
        ['org_id', 'error_type'],
        registry=REGISTRY
    )

    JOB_SUCCESS = Counter(
        'analytics_job_success_total',
        'Total number of successful analytics jobs',
        ['org_id'],
        registry=REGISTRY
    )

    ROWS_PROCESSED = Counter(
        'analytics_rows_processed_total',
        'Total number of transaction rows processed',
        ['org_id'],
        registry=REGISTRY
    )

    @contextmanager
    def track_job_duration(org_id: int, range_key: str) -> Generator[None, None, None]:
        """Context manager to track job duration and success/failure."""
        start = time.perf_counter()
        try:
            yield
            JOB_SUCCESS.labels(org_id=str(org_id)).inc()
        except Exception as e:
            JOB_FAILURE.labels(org_id=str(org_id), error_type=type(e).__name__).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            JOB_DURATION.labels(org_id=str(org_id), range_key=range_key).observe(duration)

    def record_rows_processed(org_id: int, count: int) -> None:
        """Record the number of rows processed for an org."""
        ROWS_PROCESSED.labels(org_id=str(org_id)).inc(count)

    def get_metrics() -> bytes:
        """Get all metrics in Prometheus text format."""
        return generate_latest(REGISTRY)

else:
    # Fallback implementations when prometheus_client is not installed
    @contextmanager
    def track_job_duration(org_id: int, range_key: str) -> Generator[None, None, None]:
        """No-op context manager when prometheus is not available."""
        yield

    def record_rows_processed(org_id: int, count: int) -> None:
        """No-op when prometheus is not available."""
        pass

    def get_metrics() -> bytes:
        """Return empty metrics when prometheus is not available."""
        return b""


__all__ = ["track_job_duration", "record_rows_processed", "get_metrics"]
