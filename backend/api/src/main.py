import io
import json
import logging
import mimetypes
import os
import tempfile
from datetime import datetime, timedelta
from typing import Literal

try:  # pragma: no cover - optional dependency
    import filetype  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    filetype = None  # type: ignore

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from .cache.idempotency_cache import idempotency_cache
from .config import settings
from .database import Base, engine, get_db
from .models import Document, InventoryItem, InventoryMovement, Transaction, Upload
from .schemas import (
    AccountingRequest,
    DocumentDetail,
    DocumentRead,
    InventoryMovementRow,
    InventorySummaryRow,
    UploadCreateResponse,
    UploadListRow,
)
from .assistant import OpenAIClient
from .balance_sheet import compute_roi, generate_balance_sheet, generate_pnl
from .excel_cleaner import clean_table, load_table
from .repositories.documents import DocumentRepo
from .repositories.subscription import SubscriptionRepo
from .repositories.transaction import TransactionRepo
from .rate_limit import enforce_upload_rate_limit
from .routers import analytics as analytics_router
from .routers import auth as auth_router
from .routers import inventory as inventory_router
from .routers import journal as journal_router
from .routers import settings as settings_router
from .security import AuthContext, require_plan
from .httpx_compat import ensure_async_client_app_support
from .storage import store_file
from .tasks import enqueue_upload_processing

ensure_async_client_app_support()

logging.basicConfig(
    filename="hissabi.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
app = FastAPI(title=settings.app_name, version="0.2.0")

# CORS Configuration
from fastapi.middleware.cors import CORSMiddleware

# Use CORS_ORIGINS from settings (set via env var)
# This includes Railway frontend URL when CORS_ORIGINS is configured
_cors_origins = list(settings.cors_origins)  # From CORS_ORIGINS env var
# Add common development origins if not already present
for origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
    if origin not in _cors_origins:
        _cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router)
app.include_router(inventory_router.router)
app.include_router(analytics_router.router)
app.include_router(settings_router.router)
app.include_router(journal_router.router)

JWT_SECRET = settings.jwt_secret
JWT_EXPIRE_MINUTES = settings.jwt_access_minutes
FILE_MAX_MB = settings.upload_max_mb

ALLOWED_CT = set(settings.allowed_mime_types)


async def _persist_uploaded_document(
    file: UploadFile,
    auth: AuthContext,
    db: AsyncSession,
    *,
    upload_id: int | None = None,
) -> Document:
    data = await file.read()
    if len(data) > FILE_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    ct = None
    if filetype is not None:  # pragma: no branch
        try:
            kind = filetype.guess(data)
            ct = kind.mime if kind else None
        except Exception:  # pragma: no cover - defensive
            ct = None
    if not ct:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        ct = guessed or file.content_type
    if ct not in ALLOWED_CT:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    storage_path = store_file(
        auth.user.org_id,
        file.filename,
        data,
        upload_id=upload_id,
    )
    doc = await DocumentRepo().create(
        db,
        org_id=auth.user.org_id,
        filename=file.filename,
        content_type=ct,
        storage_path=storage_path,
        size_bytes=len(data),
    )
    return doc


# --------------------- Startup (Dev DB bootstrap) ---------------------
@app.on_event("startup")
async def on_startup():
    # In production, manage schema with Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# --------------------- Uploads ---------------------
@app.post("/documents/upload", response_model=dict)
async def documents_upload(
    file: UploadFile = File(...),
    _: None = Depends(enforce_upload_rate_limit),
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    doc = await _persist_uploaded_document(file, auth, db, upload_id=upload.id)
    await db.commit()
    return {"document_id": doc.id}

# Backward-compatible alias with earlier route style
@app.post("/upload/document", response_model=dict)
async def upload_document_compat(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    return await documents_upload(file=file, auth=auth, db=db)

@app.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    docs = await DocumentRepo().list(db, auth.user.org_id)
    return [DocumentRead(
        id=d.id, org_id=d.org_id, filename=d.filename, content_type=d.content_type, 
        storage_path=d.storage_path, size_bytes=d.size_bytes, created_at=d.created_at, doc_type=d.doc_type
    ) for d in docs]

@app.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    doc = await DocumentRepo().get_owned(db, auth.user.org_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(  # type: ignore[arg-type]
        id=doc.id,
        org_id=doc.org_id,
        upload_id=doc.upload_id,
        doc_type=doc.doc_type,
        filename=doc.filename,
        content_type=doc.content_type,
        storage_path=doc.storage_path,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at,
        metadata_json=doc.metadata_json,
        url=None,
    )


# --------------------- Uploads ---------------------
@app.post("/uploads", response_model=UploadCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_upload(
    request: Request,
    file: UploadFile = File(...),
    _: None = Depends(enforce_upload_rate_limit),
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    idempotency_header = request.headers.get("Idempotency-Key")
    cache_key = None
    if idempotency_header:
        cache_key = f"upload:{auth.user.org_id}:{idempotency_header}"
        cached = await idempotency_cache.get(cache_key)
        if cached:
            return UploadCreateResponse(**cached)

    upload = Upload(org_id=auth.user.org_id, filename=file.filename, status="pending")
    db.add(upload)
    await db.flush()

    doc = await _persist_uploaded_document(file, auth, db, upload_id=upload.id)
    doc.upload_id = upload.id
    db.add(upload)

    await db.commit()

    await enqueue_upload_processing(upload.id, auth.user.org_id, doc.storage_path)

    payload = UploadCreateResponse(id=upload.id, status=upload.status, document_id=doc.id)
    if cache_key:
        await idempotency_cache.set(cache_key, payload.model_dump())
    return payload

@app.get("/uploads", response_model=list[UploadListRow])
async def list_uploads(
    auth: AuthContext = Depends(require_plan("documents")),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Upload)
        .where(Upload.org_id == auth.user.org_id)
        .order_by(Upload.uploaded_at.desc())
    )
    uploads = rows.scalars().all()
    return [
        UploadListRow(id=u.id, filename=u.filename, status=u.status, uploaded_at=u.uploaded_at)
        for u in uploads
    ]


# --------------------- Accounting generator ---------------------
@app.post("/accounting/generate", response_model=dict)
async def generate_accounting(
    payload: AccountingRequest,
    auth: AuthContext = Depends(require_plan("analytics_basic")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    windows = {
        "1m": (now - timedelta(days=30), now),
        "3m": (now - timedelta(days=90), now),
        "6m": (now - timedelta(days=180), now),
        "1y": (now - timedelta(days=365), now),
    }

    trepo = TransactionRepo()
    response: dict = {"windows": {}, "generated": []}

    for w in payload.windows:
        start, end = windows[w.kind]
        tx = await trepo.window(db, auth.user.org_id, start, end)
        rows = [
            {
                "Account": t.account_code,
                "Category": t.category,
                "Amount": t.amount,
                "Date": t.txn_date,
                "Description": t.description,
            }
            for t in tx
        ]

        out: dict = {}
        if "balance_sheet" in payload.outputs:
            out["balance_sheet"] = generate_balance_sheet(rows)
        if "pnl" in payload.outputs:
            pnl = generate_pnl(rows); out["pnl"] = pnl
            if "roi" in payload.outputs:
                out["roi"] = compute_roi(pnl)
        # cost breakdowns
        if "cost_breakdown" in payload.outputs or "cost_breakdown_pct" in payload.outputs:
            expenses = out.get("pnl", {}).get("expenses", {}) if out.get("pnl") else {}
            total_cost = sum(abs(v) for v in expenses.values())
            out["cost_breakdown"] = {"total_cost": total_cost, "by_account": expenses}
            if total_cost:
                out["cost_breakdown_pct"] = {k: (abs(v)/total_cost) for k, v in expenses.items()}
        # unit cost % from inventory
        if "unit_cost_pct" in payload.outputs:
            inv_rows = (await db.execute(
                select(InventoryItem.name, func.avg(InventoryMovement.unit_cost))
                .join(InventoryMovement, InventoryMovement.item_id==InventoryItem.id, isouter=True)
                .where(InventoryItem.org_id==auth.user.org_id)\
                .group_by(InventoryItem.name)
            )).all()
            avg_map = {name: float(avg) for name, avg in inv_rows if avg is not None}
            s = sum(avg_map.values()) or 1.0
            out["unit_cost_pct"] = {k: v/s for k, v in avg_map.items()}
        # simple projection from average monthly revenue in window
        if "sales_projection" in payload.outputs:
            rev = out.get("pnl", {}).get("revenue", 0.0)
            months = max(1, (end - start).days // 30)
            monthly = rev / months
            out["sales_projection"] = {
                "baseline_monthly": monthly,
                "conservative": monthly * 0.85,
                "optimistic": monthly * 1.15,
            }

        response["windows"][w.kind] = out

    if payload.use_llm:
        llm = OpenAIClient()
        doc = llm.generate_documents(context=response, request=payload.model_dump())
        response["llm"] = doc

    return response


# --------------------- Assistant Q&A ---------------------
@app.post("/assistant/ask", response_model=dict)
async def assistant_qa(
    body: dict,
    auth: AuthContext = Depends(require_plan("assistant")),
    db: AsyncSession = Depends(get_db),
):
    # expects {"balance": {...}, "question": "..."}
    bal = body.get("balance") or {}
    q = body.get("question") or ""
    if not q:
        raise HTTPException(status_code=400, detail="question is required")
    llm = OpenAIClient()
    answer = llm.answer_question(bal, q)
    return {"answer": answer}


# --------------------- Stripe webhook ---------------------
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import stripe
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    secret = settings.stripe_webhook_secret or ""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid signature")
    await SubscriptionRepo().upsert_from_stripe_event(db, event)
    await db.commit()
    return {"status": "ok"}


# --------------------- Health ---------------------
@app.get("/health", response_model=dict)
async def health():
    return {"status": "ok"}

@app.get("/healthz", response_model=dict)
async def health_compat():
    return await health()

@app.get("/version", response_model=dict)
async def version():
    return {"version": app.version}
