FROM python:3.12-slim

# 2. set workdir
WORKDIR /app

# 3. install runtime deps
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# 4. copy source
COPY src src

# 5. start uvicorn pointing at src/main.py
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]