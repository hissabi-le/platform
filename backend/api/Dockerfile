# backend/api/Dockerfile

# base image
FROM python:3.12-slim

# set workdir
WORKDIR /app
COPY alembic.ini .

# install runtime deps
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
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
    setuptools \
    wheel\
    openai\
    pandas\
    numpy \
    pytest\
    httpx==0.23.3 \
    pytest-asyncio\
    openpyxl \
    aiosqlite

# copy source + alembic scripts if need migrations at runtime
COPY src       src
COPY alembic   alembic

# default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
