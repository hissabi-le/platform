# backend/analytics-worker/Dockerfile

# use the official slim Python image
FROM python:3.12-slim

# set working directory
WORKDIR /app

# install runtime dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir celery

# copy our worker code
COPY src src

# default command: run the worker placeholder
CMD ["python", "src/main.py"]
