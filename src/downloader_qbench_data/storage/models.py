"""SQLAlchemy models for persisted data."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class."""


class Customer(Base):
    """Represents a QBench customer."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
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


class Batch(Base):
    """Represents a QBench batch."""

    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assay_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_prepared: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sample_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    test_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Sample(Base):
    """Represents a QBench sample."""

    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sample_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_formatted_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", deferrable=True, initially="DEFERRED"), nullable=False
    )
    has_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    batch_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    matrix_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    test_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Test(Base):
    """Represents a QBench test."""

    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sample_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("samples.id", deferrable=True, initially="DEFERRED"), nullable=False
    )
    batch_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    date_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    has_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_completed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    label_abbr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worksheet_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
    last_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
