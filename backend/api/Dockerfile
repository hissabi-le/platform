# backend/api/Dockerfile

# base image
FROM python:3.12-slim

# set workdir
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data/uploads /app/logs && \
    chown -R appuser:appuser /app

COPY alembic.ini .

# install runtime deps
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    gunicorn \
    sqlalchemy>=2.0.0 \
    asyncpg \
    alembic \
    greenlet \
    pydantic-settings \
    boto3 \
    stripe\
    passlib[bcrypt] \
    argon2-cffi \
    redis \
    clamd \
    dramatiq[redis] \
    pyjwt \
    setuptools \
    wheel\
    openai\
    pandas\
    numpy \
    pytest\
    httpx==0.23.3 \
    pytest-asyncio\
    openpyxl \
    aiosqlite \
    filetype \
    sentry-sdk[fastapi]

# copy source + alembic scripts if need migrations at runtime
COPY src       src
COPY alembic   alembic

# Switch to non-root user
USER appuser

# default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

