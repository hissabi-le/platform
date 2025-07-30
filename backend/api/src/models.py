from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    String,
    Integer,
    DateTime,
    Float,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisations"
    __table_args__ = (UniqueConstraint("name", name="uq_organisations_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    users: Mapped[list[User]] = relationship("User", back_populates="organisation")
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription", back_populates="organisation"
    )
    uploads: Mapped[list[Upload]] = relationship("Upload", back_populates="organisation")
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="organisation"
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    hashed_password: Mapped[str] = mapped_column(String(1024))
    role: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    organisation: Mapped[Organisation] = relationship("Organisation", back_populates="users")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "stripe_subscription_id", name="uq_subscriptions_stripe_subscription_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    stripe_subscription_id: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    organisation: Mapped[Organisation] = relationship(
        "Organisation", back_populates="subscriptions"
    )


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    status: Mapped[str] = mapped_column(String(50))

    organisation: Mapped[Organisation] = relationship("Organisation", back_populates="uploads")
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(
        "IngestionRun", back_populates="upload"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="upload"
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_msg: Mapped[Optional[str]] = mapped_column(Text)

    upload: Mapped[Upload] = relationship("Upload", back_populates="ingestion_runs")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="SET NULL"))
    txn_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    account_code: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10))
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    organisation: Mapped[Organisation] = relationship("Organisation", back_populates="transactions")
    upload: Mapped[Upload] = relationship("Upload", back_populates="transactions")
