# Analytics Worker

Celery worker responsible for the heavy, long-running analytics workloads:

- Streaming transactions out of Postgres with async SQLAlchemy.
- Recomputing profit & loss snapshots, ROI, and time-series data for each organisation.
- Publishing the results into Redis (`analytics:pnl:{org_id}:{range}`) so the FastAPI service can respond instantly.
- Fan-out refresh jobs (one task per organisation) and job status tracking via Redis.

## Running locally

```bash
cd backend/analytics-worker
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
DATABASE_URL=postgresql+asyncpg://... \
REDIS_URL=redis://localhost:6379/0 \
python src/main.py
```

Or rely on Docker:

```bash
docker compose up worker
```

## Key files

| File | Purpose |
| --- | --- |
| `src/analytics_worker/config.py` | Pydantic settings (Redis, Celery broker, DB pool, analytics ranges/TTL). |
| `src/analytics_worker/db.py` | Async SQLAlchemy engine/session helpers. |
| `src/analytics_worker/cache.py` | Redis-backed cache + job store + distributed lock helper. |
| `src/analytics_worker/repositories/*` | Lightweight query helpers for transactions & organisations. |
| `src/analytics_worker/services/analytics.py` | Streaming P&L aggregation and ROI computation. |
| `src/analytics_worker/tasks.py` | Celery app definition and public tasks (`refresh_org_analytics`, `refresh_all_orgs`). |
| `src/main.py` | Entrypoint (`python src/main.py` spins up a Celery worker). |

## Environment variables

| Name | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///tmp/analytics_worker.db` | Async SQLAlchemy URL for the primary DB. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker/cache endpoint. |
| `CELERY_BROKER_URL` | `REDIS_URL` | Override to point Celery at a different broker. |
| `CELERY_RESULT_BACKEND` | `REDIS_URL` | Optional Celery result backend. |
| `ANALYTICS_RANGE_WINDOWS` | `1m=30,3m=90,6m=180,1y=365` | Comma-separated list controlling which ranges we recompute. |
| `ANALYTICS_CACHE_TTL_SECONDS` | `900` | TTL for the analytics cache payloads. |
| `ANALYTICS_QUERY_BATCH_SIZE` | `2000` | Chunk size when streaming transactions. |
| `WORKER_CONCURRENCY` | `2` | Celery worker concurrency setting when using `src/main.py`. |

## Tasks

- `refresh_org_analytics(org_id, ranges=None, reason=None)` – recompute analytics for one organisation, guarded by a Redis lock and recorded in the job store.
- `refresh_all_orgs(ranges=None, reason=None)` – enumerates all organisation IDs and dispatches `refresh_org_analytics` tasks via a Celery group.
- `worker_healthcheck()` – simple readiness probe used by k8s/Docker health checks.

## Tests

Unit tests live in `backend/analytics-worker/backend/analytics-worker/tests`. Run them via:

```bash
cd backend/analytics-worker
pytest
```

They use SQLite + the same SQLAlchemy metadata, so no external services are required for CI.
