# backend/api/src/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

# --------------------------------------------------------------------
# Shared constrained types
# --------------------------------------------------------------------
Id = Annotated[int, Field(ge=1)]
ShortStr = Annotated[str, Field(min_length=1, max_length=64)]
MedStr = Annotated[str, Field(min_length=1, max_length=255)]
LongStr = Annotated[str, Field(min_length=1, max_length=1000)]
CurrencyCode = Literal["LBP", "USD", "EUR"]  # extend as needed
# Monetary values as Decimal to avoid float drift on inputs
Money = Annotated[Decimal, Field(max_digits=18, decimal_places=4)]
Qty = Annotated[Decimal, Field(max_digits=18, decimal_places=6)]
UnitStr = Annotated[str, Field(min_length=1, max_length=32)]  # keep flexible (kg, dozen, piece, etc.)

# Pydantic v2 config helper
ORM_CONFIG = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------
# Organisation
# --------------------------------------------------------------------
class OrganisationBase(BaseModel):
    name: MedStr


class OrganisationCreate(OrganisationBase):
    pass


class OrganisationRead(OrganisationBase):
    id: Id
    created_at: datetime
    model_config = ORM_CONFIG


# --------------------------------------------------------------------
# Users & Auth
# --------------------------------------------------------------------
class UserCreate(BaseModel):
    """
    Public sign-up used by /auth/register.
    We accept org_name here; org_id/role are server-assigned.
    """
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    org_name: MedStr

    @field_validator("email", mode="before")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower().strip()


class UserCreateInternal(BaseModel):
    """
    Admin/provisioning path for creating users inside an existing org.
    """
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    org_id: Id
    role: Literal["user", "admin"] = "user"

    @field_validator("email", mode="before")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower().strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email", mode="before")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower().strip()


class UserOut(BaseModel):
    id: Id
    email: EmailStr
    org_id: Id
    role: Literal["user", "admin"] = "user"


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# --------------------------------------------------------------------
# Subscriptions
# --------------------------------------------------------------------
class SubscriptionBase(BaseModel):
    org_id: Id
    plan: Literal["starter", "pro", "enterprise"]
    status: Literal["active", "past_due", "canceled"]
    stripe_subscription_id: Optional[MedStr] = None


class SubscriptionRead(SubscriptionBase):
    id: Id
    created_at: datetime
    model_config = ORM_CONFIG


# --------------------------------------------------------------------
# Uploads / Ingestion runs (if/when used by your pipeline)
# --------------------------------------------------------------------
class UploadBase(BaseModel):
    org_id: Id
    filename: MedStr
    status: Literal["pending", "processing", "done", "error"]


class UploadCreate(UploadBase):
    pass


class UploadRead(UploadBase):
    id: Id
    uploaded_at: datetime
    model_config = ORM_CONFIG


class IngestionRunBase(BaseModel):
    upload_id: Id
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_msg: Optional[LongStr] = None


class IngestionRunRead(IngestionRunBase):
    id: Id
    model_config = ORM_CONFIG


# --------------------------------------------------------------------
# Transactions (generic analytics ledger)
# --------------------------------------------------------------------
class TransactionBase(BaseModel):
    org_id: Id
    upload_id: Id
    txn_date: datetime
    account_code: ShortStr
    category: ShortStr
    amount: Money
    currency: CurrencyCode = "LBP"
    description: Optional[MedStr] = None
    metadata: Optional[dict[str, Any]] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: Id
    model_config = ORM_CONFIG


# --------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------
class DocumentRead(BaseModel):
    id: Id
    org_id: Id
    upload_id: Optional[Id] = None
    doc_type: ShortStr
    filename: MedStr
    content_type: ShortStr
    storage_path: str
    size_bytes: Annotated[int, Field(ge=0)]
    created_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ORM_CONFIG


# --------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------
class InventoryItemIn(BaseModel):
    name: MedStr
    unit: UnitStr = "unit"
    sku: Optional[ShortStr] = None
    category: Optional[ShortStr] = None


class InventoryItemOut(BaseModel):
    id: Id
    name: MedStr
    unit: UnitStr
    sku: Optional[ShortStr] = None
    category: Optional[ShortStr] = None


class InventoryMovementIn(BaseModel):
    item_id: Id
    ts: Optional[datetime] = None
    qty_delta: Qty
    unit_cost: Optional[Money] = None
    memo: Optional[MedStr] = None


class InventorySummaryRow(BaseModel):
    item_id: Id
    name: MedStr
    unit: UnitStr
    on_hand: float
    avg_unit_cost: Optional[float] = None  # outputs are computed server-side as floats


# --------------------------------------------------------------------
# Accounting / Analytics
# --------------------------------------------------------------------
class FinancialWindow(BaseModel):
    kind: Literal["1m", "3m", "6m", "1y"] = "1m"


class AccountingRequest(BaseModel):
    windows: list[FinancialWindow] = Field(
        default_factory=lambda: [FinancialWindow()],
        description="Time windows to compute (1m/3m/6m/1y).",
    )
    outputs: list[
        Literal[
            "balance_sheet",
            "pnl",
            "roi",
            "cost_breakdown",
            "cost_breakdown_pct",
            "unit_cost_pct",
            "sales_projection",
            "scenarios",
        ]
    ] = Field(
        default_factory=lambda: ["balance_sheet", "pnl"],
        description="Which documents to generate.",
    )
    use_llm: bool = Field(
        default=True,
        description="If true, overlay LLM-generated docs/scenarios when available.",
    )
