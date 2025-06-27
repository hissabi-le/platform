from python:3.12-slim
workdir /app
copy pyproject.toml .
run pip install --no-cache-dir fastapi uvicorn[standard]
copy src src
cmd ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
