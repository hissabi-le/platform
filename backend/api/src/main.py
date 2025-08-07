import os
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, AuthenticationBackend, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase as _SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, async_session, engine
from .models import Base, User, Document
from .schemas import UserCreate, UserRead, DocumentRead
from .repositories.subscription import SubscriptionRepo
from .repositories.documents import DocumentRepo
from . import assistant, balance_sheet, excel_cleaner

import logging, os

# Configure logging to file
logging.basicConfig(filename="hissabi.log", level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

if os.getenv("OPENAI_API_KEY") is None:
    os.environ["OPENAI_API_KEY"] = "<YOUR_OPENAI_API_KEY>"


app = FastAPI()
VERSION = "0.1.0"

last_balance_sheet_result = None

@app.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    """
    Upload an Excel file and get back the generated balance sheet.
    """
    # read file content into memory
    data = await file.read()
    # clean and process the excel file
    df_clean = excel_cleaner.clean_excel(io.BytesIO(data))
    result = balance_sheet.generate_balance_sheet(df_clean)
    # store result for later Q&A
    global last_balance_sheet_result
    last_balance_sheet_result = result
    # return the balance sheet result as JSON
    return {"balance_sheet": result}

@app.get("/ask-assistant")
def ask_assistant(question: str):
    """
    Ask a question about the last processed balance sheet.
    """
    if last_balance_sheet_result is None:
        return {"error": "No balance sheet available. Please upload a file first."}
    answer = assistant.answer_question(last_balance_sheet_result, question)
    return {"question": question, "answer": answer}

# override SQLAlchemyUserDatabase.create to ignore safe=True
class UserDatabase(_SQLAlchemyUserDatabase[User, int]):
    async def create(self, create_dict, safe: bool = False, **kwargs):
        # remove any extraneous kwargs
        kwargs.pop("safe", None)
        kwargs.pop("request", None)
        return await super().create(create_dict, safe = False)

async def get_user_db() -> UserDatabase:
    async with async_session() as session:
        yield UserDatabase(session, User)

# FastAPI-Users setup
cookie_transport = CookieTransport(cookie_max_age=3600)

def get_jwt_strategy() -> JWTStrategy:
    secret = os.getenv("SECRET", "changeme")
    return JWTStrategy(secret=secret, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](
    get_user_db,
    [auth_backend]
)

current_user = fastapi_users.current_user(active=True)

# auto-migrate on startup (dev only)
MIGRATE_ON_STARTUP = os.getenv("MIGRATE_ON_STARTUP", "false").lower() == "true"
if MIGRATE_ON_STARTUP:
    @app.on_event("startup")
    async def on_startup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


# health and version
@app.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/version")
async def version():
    return {"version": VERSION}

# Auth routes
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

def get_current_active_user(allowed_roles: List[str] | None = None):
    async def dependency(user: User = Depends(current_user)) -> User:
        if not user.is_active:
            raise HTTPException(status_code=400, detail="inactive user")
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return user
    return dependency

def require_plan(plan_name: str):
    async def dep(
        user: User = Depends(get_current_active_user()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        sub = await SubscriptionRepo().get_by_org(db, user.org_id)
        if not sub or sub.plan != plan_name or sub.status != "active":
            raise HTTPException(status_code=402, detail="payment required")
        return user
    return dep

# Documents listing
@app.get(
    "/documents",
    response_model=List[DocumentRead],
    summary="List all documents for your organization",
)
async def list_documents(
    user: User = Depends(get_current_active_user()),
    db: AsyncSession = Depends(get_db),
):
    docs = await DocumentRepo().list_by_org(db, user.org_id)
    return docs

# Stripe webhook
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
    if event["type"] in {"invoice.paid", "customer.subscription.updated"}:
        await SubscriptionRepo().upsert_from_stripe_event(db, event)
    return {"status": "ok"}
