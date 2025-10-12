import os, io, tempfile, logging, filetype, json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from passlib.context import CryptContext
import jwt

from .database import get_db, engine, Base
from .models import User, Organisation, Subscription, Document, InventoryItem, InventoryMovement, Transaction
from .schemas import (
    UserCreate, UserLogin, UserOut, TokenOut, DocumentRead,
    InventoryItemIn, InventoryItemOut, InventoryMovementIn, InventorySummaryRow,
    AccountingRequest,
)
from .repositories.user import UserRepo, verify_password
from .repositories.documents import DocumentRepo
from .repositories.subscription import SubscriptionRepo
from .repositories.transaction import TransactionRepo
from .excel_cleaner import load_table, clean_table
from .assistant import OpenAIClient
from .balance_sheet import generate_balance_sheet, generate_pnl, compute_roi

logging.basicConfig(filename="hissabi.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
app = FastAPI(title="Hissabi API", version="0.2.0")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
http_bearer = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
FILE_MAX_MB = int(os.getenv("FILE_MAX_MB", "20"))
STORAGE_ROOT = os.getenv("STORAGE_LOCAL_PATH", "./var/storage")

ALLOWED_CT = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
}


# --------------------- Startup (Dev DB bootstrap) ---------------------
@app.on_event("startup")
async def on_startup():
    # In production, manage schema with Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# --------------------- Security helpers ---------------------
def _hash(p: str) -> str:
    return pwd_ctx.hash(p)

def _create_jwt(sub: str, org_id: int, role: str = "user") -> str:
    now = datetime.utcnow()
    payload = {
        "sub": sub,
        "org": org_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def _auth_guard(creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        return {"user_id": int(payload["sub"]), "org_id": int(payload["org"]), "role": payload.get("role", "user")}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def _org_guard(tok = Depends(_auth_guard), db: AsyncSession = Depends(get_db)):
    u = await db.scalar(select(User).where(User.id == tok["user_id"], User.org_id == tok["org_id"]))
    if not u:
        raise HTTPException(status_code=403, detail="Invalid tenancy")
    sub = await SubscriptionRepo().active_for_org(db, tok["org_id"])
    if not sub:
        raise HTTPException(status_code=402, detail="Subscription required")
    return tok


# --------------------- Auth ---------------------
@app.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await UserRepo().by_email(db, payload.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await UserRepo().create_with_org(db, payload.email, payload.password, payload.org_name)
    db.add(Subscription(org_id=user.org_id, plan="starter", status="active"))
    await db.commit(); await db.refresh(user)
    token = _create_jwt(str(user.id), user.org_id, role=user.role)
    return TokenOut(access_token=token)

@app.post("/auth/login", response_model=TokenOut)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await UserRepo().by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_jwt(str(user.id), user.org_id, role=user.role)
    return TokenOut(access_token=token)

@app.get("/users/me", response_model=UserOut)
async def me(tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    u = await db.get(User, tok["user_id"])
    return UserOut(id=u.id, email=u.email, org_id=u.org_id, role=u.role)  # type: ignore


# --------------------- Uploads ---------------------
@app.post("/documents/upload", response_model=dict)
async def documents_upload(file: UploadFile = File(...), tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    data = await file.read()
    if len(data) > FILE_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    kind = filetype.guess(data)
    ct = kind.mime if kind else file.content_type
    if ct not in ALLOWED_CT:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    org_dir = os.path.join(STORAGE_ROOT, str(tok["org_id"]))
    os.makedirs(org_dir, exist_ok=True)
    path = os.path.join(org_dir, file.filename)
    with open(path, "wb") as out:
        out.write(data)
    doc = await DocumentRepo().create(db,
        org_id=tok["org_id"], filename=file.filename, content_type=ct, storage_path=path, size_bytes=len(data)
    )
    await db.commit()
    return {"document_id": doc.id}

# Backward-compatible alias with earlier route style
@app.post("/upload/document", response_model=dict)
async def upload_document_compat(file: UploadFile = File(...), tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    return await documents_upload(file=file, tok=tok, db=db)

@app.get("/documents", response_model=list[DocumentRead])
async def list_documents(tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    docs = await DocumentRepo().list(db, tok["org_id"])
    return [DocumentRead(
        id=d.id, filename=d.filename, content_type=d.content_type, size_bytes=d.size_bytes, created_at=d.created_at, doc_type=d.doc_type
    ) for d in docs]


# --------------------- Inventory ---------------------
UNIT_ALIASES = {"kilograms":"kg","kilos":"kg","kg":"kg","dozen":"dozen","dz":"dozen","pcs":"piece","pieces":"piece","unit":"unit"}

def _norm_unit(u: str | None) -> str:
    if not u: return "unit"
    k = str(u).strip().lower(); return UNIT_ALIASES.get(k, k)

@app.post("/inventory/extract/{document_id}", response_model=dict)
async def inventory_extract(document_id: int, tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    doc = await DocumentRepo().get_owned(db, tok["org_id"], document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Load table
    with open(doc.storage_path, "rb") as f:
        buf = f.read()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(buf); tmp.flush(); path = tmp.name
    try:
        df = load_table(path); df = clean_table(df)
    finally:
        try: os.unlink(path)
        except Exception: pass

    rows = df.to_dict(orient="records")

    # LLM mapping with offline fallback
    llm = OpenAIClient()
    mapped = llm.map_rows_to_inventory(rows)

    created_movements = 0
    for r in mapped:
        item = r.get("Item") or r.get("item")
        if not item:
            continue
        qty = r.get("Qty")
        unit = _norm_unit(r.get("Unit"))
        amount = r.get("Amount")
        sku = r.get("SKU")

        # upsert item by (name, unit, org)
        exist = await db.scalars(
            select(InventoryItem).where(InventoryItem.org_id==tok["org_id"], InventoryItem.name==item, InventoryItem.unit==unit)
        )
        item_row = exist.first()
        if not item_row:
            item_row = InventoryItem(org_id=tok["org_id"], name=item, unit=unit, sku=sku)
            db.add(item_row); await db.flush()

        unit_cost = (amount/qty) if (amount and qty and qty != 0) else None
        if qty is not None:
            db.add(InventoryMovement(
                org_id=tok["org_id"], item_id=item_row.id, qty_delta=float(qty), unit_cost=unit_cost,
                ref_document_id=doc.id, memo="auto-LLM"
            ))
            created_movements += 1

    await db.commit()
    return {"created_movements": created_movements}

@app.get("/inventory/summary", response_model=list[InventorySummaryRow])
async def inventory_summary(tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(
            InventoryItem.id, InventoryItem.name, InventoryItem.unit,
            func.coalesce(func.sum(InventoryMovement.qty_delta), 0).label("on_hand"),
            func.avg(InventoryMovement.unit_cost).label("avg_unit_cost")
        )
        .join(InventoryMovement, InventoryMovement.item_id == InventoryItem.id, isouter=True)
        .where(InventoryItem.org_id == tok["org_id"])\
        .group_by(InventoryItem.id)
        .order_by(InventoryItem.name)
    )).all()

    return [InventorySummaryRow(
        item_id=r.id, name=r.name, unit=r.unit,
        on_hand=float(r.on_hand or 0),
        avg_unit_cost=float(r.avg_unit_cost) if r.avg_unit_cost is not None else None
    ) for r in rows]


# --------------------- Accounting generator ---------------------
@app.post("/accounting/generate", response_model=dict)
async def generate_accounting(payload: AccountingRequest, tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
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
        tx = await trepo.window(db, tok["org_id"], start, end)
        rows = [dict(ts=t.ts.isoformat(), account=t.account, amount=t.amount, description=t.description) for t in tx]

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
                .where(InventoryItem.org_id==tok["org_id"])\
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
async def assistant_qa(body: dict, tok = Depends(_org_guard), db: AsyncSession = Depends(get_db)):
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
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
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
