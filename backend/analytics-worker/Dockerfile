# backend/analytics-worker/Dockerfile

# use the official slim Python image
FROM python:3.12-slim

WORKDIR /app

# install system deps (build essentials for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src src

RUN pip install --no-cache-dir .

CMD ["python", "src/main.py"]
