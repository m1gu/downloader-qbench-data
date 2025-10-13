"""SQLAlchemy models for persisted data."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class."""


class Customer(Base):
    """Represents a QBench customer."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Order(Base):
    """Represents a QBench order."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    custom_formatted_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", deferrable=True, initially="DEFERRED"), nullable=False
    )
    date_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_completed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_order_reported: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_received: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    test_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SyncCheckpoint(Base):
    """Tracks last successful sync state for an entity."""

    __tablename__ = "sync_checkpoints"

    entity: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_cursor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
