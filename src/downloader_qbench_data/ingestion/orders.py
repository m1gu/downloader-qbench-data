"""Ingestion routines for QBench orders."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from downloader_qbench_data.clients.qbench import QBenchClient
from downloader_qbench_data.config import AppSettings, get_settings
from downloader_qbench_data.ingestion.utils import parse_qbench_datetime
from downloader_qbench_data.storage import Customer, Order, SyncCheckpoint, session_scope

LOGGER = logging.getLogger(__name__)
ENTITY_NAME = "orders"
API_MAX_PAGE_SIZE = 50


@dataclass
class OrderSyncSummary:
    """Aggregated statistics for an order sync run."""

    processed: int = 0
    skipped_missing_customer: int = 0
    skipped_unknown_customer: int = 0
    skipped_old: int = 0
    pages_seen: int = 0
    last_synced_at: Optional[datetime] = None
    total_pages: Optional[int] = None
    start_page: int = 1


def sync_orders(
    settings: Optional[AppSettings] = None,
    *,
    full_refresh: bool = False,
    page_size: Optional[int] = None,
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
) -> OrderSyncSummary:
    """Synchronise order data from QBench into PostgreSQL."""

    settings = settings or get_settings()
    effective_page_size = min(page_size or settings.page_size, API_MAX_PAGE_SIZE)

    with session_scope(settings) as session:
        checkpoint = _get_or_create_checkpoint(session)
        if full_refresh:
            checkpoint.last_synced_at = None
            checkpoint.last_cursor = 1
        start_page = checkpoint.last_cursor or 1
        last_synced_at = checkpoint.last_synced_at
        checkpoint.status = "running"
        checkpoint.failed = False
        checkpoint.message = None
        known_customers = _load_customer_ids(session)

    summary = OrderSyncSummary(last_synced_at=last_synced_at, start_page=start_page)
    baseline_synced_at = last_synced_at
    max_synced_at = last_synced_at
    current_page = start_page
    try:
        with QBenchClient(
            base_url=settings.qbench.base_url,
            client_id=settings.qbench.client_id,
            client_secret=settings.qbench.client_secret,
            token_url=settings.qbench.token_url,
        ) as client:
            total_pages: Optional[int] = None
            while True:
                stop_after_page = False
                payload = client.list_orders(
                    page_num=current_page,
                    page_size=effective_page_size,
                    sort_by="date_created",
                    sort_order="desc",
                )
                total_pages = payload.get("total_pages") or total_pages
                summary.total_pages = total_pages
                orders = payload.get("data") or []
                if not orders:
                    break

                summary.pages_seen += 1
                records_to_upsert = []
                for item in orders:
                    customer_id = item.get("customer_account_id")
                    if not customer_id:
                        summary.skipped_missing_customer += 1
                        continue
                    if customer_id not in known_customers:
                        summary.skipped_unknown_customer += 1
                        LOGGER.warning(
                            "Skipping order %s because customer %s does not exist locally",
                            item.get("id"),
                            customer_id,
                        )
                        continue

                    created_at = parse_qbench_datetime(item.get("date_created"))
                    if (
                        not full_refresh
                        and baseline_synced_at is not None
                        and created_at is not None
                        and created_at <= baseline_synced_at
                    ):
                        summary.skipped_old += 1
                        stop_after_page = True
                        continue

                    record = {
                        "id": item["id"],
                        "custom_formatted_id": item.get("custom_formatted_id"),
                        "customer_account_id": customer_id,
                        "date_created": created_at,
                        "date_completed": parse_qbench_datetime(item.get("date_completed")),
                        "date_order_reported": parse_qbench_datetime(item.get("date_order_reported")),
                        "date_received": parse_qbench_datetime(item.get("date_received")),
                        "sample_count": _safe_int(item.get("sample_count")),
                        "test_count": _safe_int(item.get("test_count")),
                        "state": item.get("state"),
                        "raw_payload": item,
                    }
                    records_to_upsert.append(record)
                    summary.processed += 1
                    if created_at and (max_synced_at is None or created_at > max_synced_at):
                        max_synced_at = created_at

                _persist_batch(records_to_upsert, current_page, max_synced_at, settings)
                if progress_callback:
                    progress_callback(summary.pages_seen, total_pages)

                if stop_after_page:
                    break
                if total_pages and current_page >= total_pages:
                    break
                current_page += 1

    except Exception as exc:
        LOGGER.exception("Order sync failed on page %s", current_page)
        _mark_checkpoint_failed(current_page, settings, error=exc)
        raise

    _mark_checkpoint_completed(current_page, max_synced_at, settings)
    summary.last_synced_at = max_synced_at
    return summary


def _persist_batch(
    rows: Iterable[dict],
    current_page: int,
    max_synced_at: Optional[datetime],
    settings: AppSettings,
) -> None:
    """Persist a batch of orders and update checkpoint progress."""

    with session_scope(settings) as session:
        checkpoint = _get_or_create_checkpoint(session)
        checkpoint.last_cursor = current_page
        checkpoint.status = "running"
        checkpoint.failed = False
        checkpoint.message = None

        if rows:
            insert_stmt = insert(Order).values(list(rows))
            update_stmt = {
                "custom_formatted_id": insert_stmt.excluded.custom_formatted_id,
                "customer_account_id": insert_stmt.excluded.customer_account_id,
                "date_created": insert_stmt.excluded.date_created,
                "date_completed": insert_stmt.excluded.date_completed,
                "date_order_reported": insert_stmt.excluded.date_order_reported,
                "date_received": insert_stmt.excluded.date_received,
                "sample_count": insert_stmt.excluded.sample_count,
                "test_count": insert_stmt.excluded.test_count,
                "state": insert_stmt.excluded.state,
                "raw_payload": insert_stmt.excluded.raw_payload,
                "fetched_at": func.now(),
            }
            session.execute(insert_stmt.on_conflict_do_update(index_elements=[Order.id], set_=update_stmt))
            checkpoint.last_synced_at = max_synced_at


def _mark_checkpoint_completed(current_page: int, max_synced_at: Optional[datetime], settings: AppSettings) -> None:
    """Mark the checkpoint as completed."""

    with session_scope(settings) as session:
        checkpoint = _get_or_create_checkpoint(session)
        checkpoint.last_cursor = current_page
        checkpoint.last_synced_at = max_synced_at
        checkpoint.status = "completed"
        checkpoint.failed = False
        checkpoint.message = None


def _mark_checkpoint_failed(current_page: int, settings: AppSettings, error: Exception) -> None:
    """Persist a failure state into the checkpoint."""

    with session_scope(settings) as session:
        checkpoint = _get_or_create_checkpoint(session)
        checkpoint.last_cursor = current_page
        checkpoint.failed = True
        checkpoint.status = "failed"
        checkpoint.message = str(error)


def _get_or_create_checkpoint(session: Session) -> SyncCheckpoint:
    """Fetch existing checkpoint or create one for the entity."""

    checkpoint = session.get(SyncCheckpoint, ENTITY_NAME)
    if not checkpoint:
        checkpoint = SyncCheckpoint(entity=ENTITY_NAME, status="never", failed=False)
        session.add(checkpoint)
        session.flush()
    return checkpoint


def _load_customer_ids(session: Session) -> set[int]:
    """Load all customer IDs present in the local database."""

    result = session.execute(select(Customer.id))
    return {row[0] for row in result}


def _safe_int(value: Optional[int | str]) -> Optional[int]:
    """Convert the provided value to int when possible."""

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        LOGGER.warning("Could not cast value '%s' to int", value)
        return None
