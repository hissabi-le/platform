# backend/api/src/main.py
# basic api service
from fastapi import FastAPI

app = FastAPI()
VERSION = "0.1.0"

# returns health status
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# returns current version
@app.get("/version")
async def version():
    return {"version": VERSION}
