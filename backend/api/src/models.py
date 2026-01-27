# src/models.py
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
    Numeric,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Organisation(Base):
    __tablename__ = "organisations"
    # __table_args__ = (UniqueConstraint("name", name="uq_organisations_name"),)

    id:            Mapped[int]              = mapped_column(primary_key=True)
    name:          Mapped[str]              = mapped_column(String(255), nullable=False)
    created_at:    Mapped[datetime]         = mapped_column(
                                              DateTime(timezone=True),
                                              server_default=func.now(),
                                              nullable=False,
                                          )

    users:         Mapped[List["User"]]         = relationship("User",         back_populates="organisation")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="organisation")
    uploads:       Mapped[List["Upload"]]       = relationship("Upload",       back_populates="organisation")
    transactions:  Mapped[List["Transaction"]]  = relationship("Transaction",  back_populates="organisation")
    documents:     Mapped[List["Document"]]     = relationship("Document",     back_populates="organisation")
    settings:      Mapped["OrganisationSettings"] = relationship(
        "OrganisationSettings",
        back_populates="organisation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    journal_days:  Mapped[List["JournalDay"]] = relationship("JournalDay", back_populates="organisation")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id:               Mapped[int]      = mapped_column(primary_key=True)
    org_id:           Mapped[int]      = mapped_column(
                                              ForeignKey("organisations.id", ondelete="CASCADE"),
                                              nullable=False,
                                          )
    email:            Mapped[str]      = mapped_column(String(320),  nullable=False)
    hashed_password:  Mapped[str]      = mapped_column(String(1024), nullable=False)
    role:             Mapped[str]      = mapped_column(String(50),   nullable=False)
    is_active:        Mapped[bool]     = mapped_column(nullable=False, default=True)
    created_at:       Mapped[datetime] = mapped_column(
                                              DateTime(timezone=True),
                                              server_default=func.now(),
                                              nullable=False,
                                          )

    organisation:     Mapped["Organisation"] = relationship("Organisation", back_populates="users")
    journal_days:     Mapped[List["JournalDay"]] = relationship("JournalDay", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("stripe_subscription_id", name="uq_subscriptions_stripe_subscription_id"),
    )

    id:                    Mapped[int]      = mapped_column(primary_key=True)
    org_id:                Mapped[int]      = mapped_column(
                                                  ForeignKey("organisations.id", ondelete="CASCADE"),
                                                  nullable=False,
                                              )
    stripe_subscription_id: Mapped[str]     = mapped_column(String(255), nullable=False)
    plan:                  Mapped[str]      = mapped_column(String(100), nullable=False)
    status:                Mapped[str]      = mapped_column(String(50),  nullable=False)
    created_at:            Mapped[datetime] = mapped_column(
                                                  DateTime(timezone=True),
                                                  server_default=func.now(),
                                                  nullable=False,
                                              )

    organisation:          Mapped["Organisation"] = relationship("Organisation", back_populates="subscriptions")


class Upload(Base):
    __tablename__ = "uploads"

    id:           Mapped[int]        = mapped_column(primary_key=True)
    org_id:       Mapped[int]        = mapped_column(
                                          ForeignKey("organisations.id", ondelete="CASCADE"),
                                          nullable=False,
                                      )
    filename:     Mapped[str]        = mapped_column(String(255), nullable=False)
    uploaded_at:  Mapped[datetime]   = mapped_column(
                                          DateTime(timezone=True),
                                          server_default=func.now(),
                                          nullable=False,
                                      )
    status:       Mapped[str]        = mapped_column(String(50),   nullable=False)

    organisation:   Mapped["Organisation"]     = relationship("Organisation",   back_populates="uploads")
    ingestion_runs: Mapped[List["IngestionRun"]] = relationship("IngestionRun", back_populates="upload")
    transactions:   Mapped[List["Transaction"]]  = relationship("Transaction",  back_populates="upload")
    documents:      Mapped[List["Document"]]     = relationship("Document",     back_populates="upload")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id:           Mapped[int]        = mapped_column(primary_key=True)
    upload_id:    Mapped[int]        = mapped_column(
                                          ForeignKey("uploads.id", ondelete="CASCADE"),
                                          nullable=False,
                                      )
    started_at:   Mapped[datetime]   = mapped_column(
                                          DateTime(timezone=True),
                                          server_default=func.now(),
                                          nullable=False,
                                      )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg:    Mapped[Optional[str]]      = mapped_column(Text, nullable=True)

    upload:       Mapped["Upload"]   = relationship("Upload", back_populates="ingestion_runs")


class Transaction(Base):
    __tablename__ = "transactions"

    id:            Mapped[int]        = mapped_column(primary_key=True)
    org_id:        Mapped[int]        = mapped_column(
                                           ForeignKey("organisations.id", ondelete="CASCADE"),
                                           nullable=False,
                                       )
    upload_id:     Mapped[Optional[int]] = mapped_column(
                                           ForeignKey("uploads.id", ondelete="SET NULL"),
                                           nullable=True,
                                       )
    txn_date:      Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False)
    account_code:  Mapped[str]        = mapped_column(String(50), nullable=False)
    category:      Mapped[str]        = mapped_column(String(100), nullable=False)
    amount:        Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False)
    currency:      Mapped[str]        = mapped_column(String(10), nullable=False)
    description:   Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Any]        = mapped_column(
                                           JSON,
                                           default=dict,
                                           nullable=False,
                                       )
    # AR/AP tracking: default to "paid" (settled)
    payment_status: Mapped[str]       = mapped_column(
                                           String(20), nullable=False, default="paid"
                                       )  # "paid" | "unpaid"
    payment_date:  Mapped[Optional[datetime]] = mapped_column(
                                           DateTime(timezone=True), nullable=True
                                       )  # When marked as paid (null if unpaid or paid at creation)

    organisation:  Mapped["Organisation"] = relationship("Organisation", back_populates="transactions")
    upload:        Mapped["Upload"]       = relationship("Upload",       back_populates="transactions")


class Document(Base):
    __tablename__ = "documents"

    id:            Mapped[int]          = mapped_column(primary_key=True)
    org_id:        Mapped[int]          = mapped_column(
                                           ForeignKey("organisations.id", ondelete="CASCADE"),
                                           nullable=False,
                                       )
    upload_id:     Mapped[Optional[int]] = mapped_column(
                                           ForeignKey("uploads.id", ondelete="SET NULL"),
                                           nullable=True,
                                       )
    doc_type:      Mapped[str]          = mapped_column(Text,    nullable=False)
    filename:      Mapped[str]          = mapped_column(Text,    nullable=False)
    content_type:  Mapped[str]          = mapped_column(Text,    nullable=False)
    storage_path:  Mapped[str]          = mapped_column(Text,    nullable=False)
    size_bytes:    Mapped[int]          = mapped_column(BigInteger, nullable=False)
    created_at:    Mapped[datetime]     = mapped_column(
                                           DateTime(timezone=True),
                                           server_default=func.now(),
                                           nullable=False,
                                       )
    metadata_json: Mapped[Any]          = mapped_column(JSON, nullable=True)

    organisation:  Mapped["Organisation"] = relationship("Organisation", back_populates="documents")
    upload:        Mapped["Upload"]       = relationship("Upload",       back_populates="documents")


# -----------------------------
# Inventory (new)
# -----------------------------
class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id:       Mapped[int]      = mapped_column(primary_key=True)
    org_id:   Mapped[int]      = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    name:     Mapped[str]      = mapped_column(String(255), nullable=False)
    unit:     Mapped[str]      = mapped_column(String(32),  nullable=False, default="unit")
    sku:      Mapped[Optional[str]] = mapped_column(String(64))
    category: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organisation: Mapped["Organisation"] = relationship("Organisation")
    movements:    Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", "unit", name="uq_item_name_unit_org"),
        Index("ix_item_org_name", "org_id", "name"),
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id:        Mapped[int]       = mapped_column(primary_key=True)
    org_id:    Mapped[int]       = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    item_id:   Mapped[int]       = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    ref_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    ts:        Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    qty_delta: Mapped[Decimal]   = mapped_column(Numeric(18, 6), nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))  # required only on positive deltas
    memo:      Mapped[Optional[str]]     = mapped_column(String(255))

    item:         Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="movements")
    organisation: Mapped["Organisation"]  = relationship("Organisation")
    document:     Mapped[Optional["Document"]] = relationship("Document")

    __table_args__ = (
        Index("ix_invmove_org_item_ts", "org_id", "item_id", "ts"),
    )


# -----------------------------
# Settings & Journal
# -----------------------------


class OrganisationSettings(Base):
    __tablename__ = "organisation_settings"
    __table_args__ = (
        UniqueConstraint("org_id", name="uq_org_settings_org"),
        CheckConstraint("total_initial_investment >= 0", name="ck_settings_initial_investment_nonnegative"),
        CheckConstraint("starting_cash_balance >= 0", name="ck_settings_starting_cash_nonnegative"),
        CheckConstraint("current_assets_value >= 0", name="ck_settings_assets_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    total_initial_investment: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    starting_cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    current_assets_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    default_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    default_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    vat_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="settings")


class JournalParseStatus(str, Enum):
    PENDING = "pending"
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class JournalEntryType(str, Enum):
    REVENUE = "revenue"
    COST = "cost"
    INVENTORY_PURCHASE = "inventory_purchase"
    INVENTORY_USE = "inventory_use"
    TRANSFER = "transfer"


class JournalDay(Base):
    __tablename__ = "journal_days"
    __table_args__ = (
        UniqueConstraint("org_id", "journal_date", name="uq_journal_org_date"),
        UniqueConstraint("hash_key", name="uq_journal_hash"),
        CheckConstraint(
            "parse_status IN ('pending','parsed','needs_review','error')",
            name="ck_journal_status_valid"
        ),
        Index("ix_journal_org_date", "org_id", "journal_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    journal_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(8))
    parse_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=JournalParseStatus.PENDING.value,
    )
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    clarification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hash_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="journal_days")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="journal_days")
    entries: Mapped[List["JournalEntry"]] = relationship(
        "JournalEntry",
        back_populates="journal_day",
        cascade="all, delete-orphan",
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('revenue','cost','inventory_purchase','inventory_use','transfer')",
            name="ck_journal_entry_type_valid"
        ),
        Index("ix_journal_entry_org_day", "org_id", "journal_day_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    journal_day_id: Mapped[int] = mapped_column(ForeignKey("journal_days.id", ondelete="CASCADE"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    item_name: Mapped[Optional[str]] = mapped_column(String(255))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    unit: Mapped[Optional[str]] = mapped_column(String(32))
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    vat_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    vat_included: Mapped[Optional[bool]] = mapped_column(Boolean)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clarification_question: Mapped[Optional[str]] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # AR/AP tracking: default to "paid" (settled)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="paid")  # "paid" | "unpaid"
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # When marked as paid
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    org: Mapped["Organisation"] = relationship("Organisation")
    journal_day: Mapped["JournalDay"] = relationship("JournalDay", back_populates="entries")
