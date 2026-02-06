# backend/api/src/schemas.py
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Literal, Optional, Annotated

from email_validator import EmailNotValidError, validate_email as _validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------------------
# Shared constrained types
# --------------------------------------------------------------------
Id = Annotated[int, Field(ge=1)]
ShortStr = Annotated[str, Field(min_length=1, max_length=128)]
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


# Helper to normalise email values safely across email-validator versions
def _normalize_email(value: Any) -> str:
    if value is None:
        raise ValueError("email is required")
    email = str(value).strip()
    try:
        result = _validate_email(email, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    normalized = getattr(result, "normalized", None)
    if not normalized and isinstance(result, dict):
        normalized = result.get("normalized") or result.get("email")
    return (normalized or email).lower()


# --------------------------------------------------------------------
# Users & Auth
# --------------------------------------------------------------------
class UserCreate(BaseModel):
    """
    Public sign-up used by /auth/register.
    We accept org_name here; org_id/role are server-assigned.
    """
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    org_name: MedStr

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> str:
        return _normalize_email(value)


class UserCreateInternal(BaseModel):
    """
    Admin/provisioning path for creating users inside an existing org.
    """
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    org_id: Id
    role: Literal["user", "admin"] = "user"

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> str:
        return _normalize_email(value)


class UserLogin(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> str:
        return _normalize_email(value)


class UserOut(BaseModel):
    id: Id
    email: str
    org_id: Id
    role: Literal["user", "admin"] = "user"
    plan: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class AuthResponse(TokenPair):
    user: UserOut


class TokenRefreshRequest(BaseModel):
    refresh_token: str


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
    # AR/AP tracking
    payment_status: Literal["paid", "unpaid"] = "paid"
    payment_date: Optional[datetime] = None


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


class DocumentDetail(DocumentRead):
    url: Optional[str] = None


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


class InventoryMovementRow(BaseModel):
    ts: datetime
    quantity: float
    type: Literal["in", "out"]
    ref: Optional[str] = None


# --------------------------------------------------------------------
# Uploads exposed via API
# --------------------------------------------------------------------
class UploadListRow(BaseModel):
    id: Id
    filename: MedStr
    status: Literal["pending", "processing", "done", "error"]
    uploaded_at: datetime


class UploadCreateResponse(BaseModel):
    id: Id
    status: Literal["pending", "processing", "done", "error"]
    document_id: Optional[Id] = None


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


# --------------------------------------------------------------------
# Organisation settings
# --------------------------------------------------------------------
class OrganisationSettingsBase(BaseModel):
    total_initial_investment: Money = Field(default=Decimal("0"))
    starting_cash_balance: Money = Field(default=Decimal("0"))
    current_assets_value: Money = Field(default=Decimal("0"))
    default_currency: Annotated[str, Field(min_length=1, max_length=10)] = "USD"
    default_locale: Annotated[str, Field(min_length=2, max_length=10)] = "en"
    vat_rate: Optional[Annotated[Decimal, Field(max_digits=5, decimal_places=2)]] = None

    @field_validator(
        "total_initial_investment",
        "starting_cash_balance",
        "current_assets_value",
        mode="before",
    )
    @classmethod
    def _ensure_non_negative(cls, value: Any) -> Any:
        if value is None:
            return value
        quant = Decimal(str(value))
        if quant < 0:
            raise ValueError("value must be non-negative")
        return quant


class OrganisationSettingsRead(OrganisationSettingsBase):
    id: Id
    org_id: Id
    created_at: datetime
    updated_at: datetime
    model_config = ORM_CONFIG


class OrganisationSettingsUpdate(BaseModel):
    total_initial_investment: Optional[Money] = None
    starting_cash_balance: Optional[Money] = None
    current_assets_value: Optional[Money] = None
    default_currency: Optional[Annotated[str, Field(min_length=1, max_length=10)]] = None
    default_locale: Optional[Annotated[str, Field(min_length=2, max_length=10)]] = None
    vat_rate: Optional[Annotated[Decimal, Field(max_digits=5, decimal_places=2)]] = None

    @field_validator(
        "total_initial_investment",
        "starting_cash_balance",
        "current_assets_value",
        mode="before",
    )
    @classmethod
    def _ensure_non_negative(cls, value: Any) -> Any:
        if value is None:
            return value
        quant = Decimal(str(value))
        if quant < 0:
            raise ValueError("value must be non-negative")
        return quant


# --------------------------------------------------------------------
# Journal (Information Sheet)
# --------------------------------------------------------------------
class JournalEntryBase(BaseModel):
    entry_type: Literal[
        "revenue",
        "cost",
        "inventory_purchase",
        "inventory_use",
        "transfer",
    ]
    item_name: Optional[MedStr] = None
    quantity: Optional[Qty] = None
    unit: Optional[UnitStr] = None
    unit_cost: Optional[Money] = None
    total: Money
    category: Optional[MedStr] = None
    vat_percent: Optional[Annotated[Decimal, Field(max_digits=5, decimal_places=2)]] = None
    vat_included: Optional[bool] = None
    notes: Optional[LongStr] = None
    ambiguous: bool = False
    clarification_question: Optional[LongStr] = None
    resolved: bool = True
    # AR/AP tracking
    payment_status: Literal["paid", "unpaid"] = "paid"
    payment_date: Optional[datetime] = None


class JournalEntryCreate(JournalEntryBase):
    pass


class JournalEntryRead(JournalEntryBase):
    # Override total to allow None for entries with parsing failures (will be marked ambiguous)
    total: Optional[Money] = None
    id: Optional[Id] = None
    created_at: Optional[datetime] = None
    model_config = ORM_CONFIG


class JournalClarification(BaseModel):
    entry_id: Optional[Id] = None
    question: LongStr
    entry_type: str
    category: Optional[MedStr] = None


class JournalTotals(BaseModel):
    revenue: Money
    cost: Money
    net: Money
    cumulative_net: Money
    roi: Optional[float] = None


class JournalDayMeta(BaseModel):
    id: Optional[Id] = None
    org_id: Id
    user_id: Optional[Id] = None
    journal_date: date
    language: Optional[str] = None
    parse_status: Literal["pending", "parsed", "needs_review", "error"]
    total_revenue: Money
    total_cost: Money
    net_profit: Money
    clarification_count: int
    created_at: datetime
    updated_at: datetime
    model_config = ORM_CONFIG


class JournalDayRequest(BaseModel):
    raw_text: Annotated[str, Field(min_length=1)]
    date: Optional[str] = None
    commit: bool = True


class JournalResolution(BaseModel):
    entry_id: Id
    entry_type: Optional[
        Literal[
            "revenue",
            "cost",
            "inventory_purchase",
            "inventory_use",
            "transfer",
        ]
    ] = None
    quantity: Optional[Qty] = None
    category: Optional[MedStr] = None
    treat_as_inventory: Optional[bool] = None
    vat_percent: Optional[Annotated[Decimal, Field(max_digits=5, decimal_places=2)]] = None
    vat_included: Optional[bool] = None
    unit: Optional[UnitStr] = None
    unit_cost: Optional[Money] = None
    notes: Optional[LongStr] = None


class JournalResolveRequest(BaseModel):
    resolutions: list[JournalResolution]


class JournalDayResponse(BaseModel):
    journal_day: JournalDayMeta
    entries: list[JournalEntryRead]
    clarifications: list[JournalClarification]
    totals: JournalTotals
