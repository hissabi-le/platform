# backend/analytics-worker/Dockerfile

# use the official slim Python image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# install system deps (build essentials for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src src

RUN pip install --no-cache-dir . sentry-sdk[celery] prometheus-client

# Switch to non-root user
USER appuser

CMD ["python", "src/main.py"]

