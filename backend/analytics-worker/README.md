# Analytics Worker

This directory houses the Celery worker that will process heavy analytics workloads (statement generation, long-running inventory enrichment, etc.).

Current status:
- Python package scaffolding (`pyproject.toml`) with Celery dependency.
- `src/` is intentionally minimal; add tasks under `src/tasks.py` when ready.
- Dockerfile builds a slim worker image used by `docker-compose.yml`.

Next steps:
1. Decide on broker/back-end configuration (Redis is provisioned in `docker-compose` and Terraform).
2. Implement Celery app/tasks that mirror the synchronous logic in `backend/api`.
3. Wire task dispatch from the API (e.g., via FastAPI background tasks or explicit Celery calls).
