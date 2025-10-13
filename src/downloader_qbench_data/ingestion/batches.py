"""Ingestion routines for QBench batches."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from downloader_qbench_data.clients.qbench import QBenchClient
from downloader_qbench_data.config import AppSettings, get_settings
from downloader_qbench_data.ingestion.utils import ensure_int_list, parse_qbench_datetime
from downloader_qbench_data.storage import Batch, SyncCheckpoint, session_scope

LOGGER = logging.getLogger(__name__)
ENTITY_NAME = "batches"
API_MAX_PAGE_SIZE = 50


@dataclass
class BatchSyncSummary:
    """Aggregated statistics for a batch sync run."""

    processed: int = 0
    skipped_old: int = 0
    pages_seen: int = 0
    last_synced_at: Optional[datetime] = None
    total_pages: Optional[int] = None
    start_page: int = 1


def sync_batches(
    settings: Optional[AppSettings] = None,
    *,
    full_refresh: bool = False,
    page_size: Optional[int] = None,
    include_raw_worksheet_data: bool = False,
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
) -> BatchSyncSummary:
    """Synchronise batch data from QBench into PostgreSQL."""

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

    summary = BatchSyncSummary(last_synced_at=last_synced_at, start_page=start_page)
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
                payload = client.list_batches(
                    page_num=current_page,
                    page_size=effective_page_size,
                    include_raw_worksheet_data=include_raw_worksheet_data,
                )
                total_pages = payload.get("total_pages") or total_pages
                summary.total_pages = total_pages
                batches = payload.get("data") or []
                if not batches:
                    break

                summary.pages_seen += 1
                records_to_upsert = []
                for item in batches:
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
                        "assay_id": item.get("assay_id"),
                        "display_name": item.get("display_name"),
                        "date_created": created_at,
                        "date_prepared": parse_qbench_datetime(item.get("date_prepared")),
                        "last_updated": parse_qbench_datetime(item.get("last_updated")),
                        "sample_ids": ensure_int_list(item.get("sample_ids")),
                        "test_ids": ensure_int_list(item.get("test_ids")),
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
        LOGGER.exception("Batch sync failed on page %s", current_page)
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
    """Persist a batch of batches and update checkpoint progress."""

    with session_scope(settings) as session:
        checkpoint = _get_or_create_checkpoint(session)
        checkpoint.last_cursor = current_page
        checkpoint.status = "running"
        checkpoint.failed = False
        checkpoint.message = None

        if rows:
            insert_stmt = insert(Batch).values(list(rows))
            update_stmt = {
                "assay_id": insert_stmt.excluded.assay_id,
                "display_name": insert_stmt.excluded.display_name,
                "date_created": insert_stmt.excluded.date_created,
                "date_prepared": insert_stmt.excluded.date_prepared,
                "last_updated": insert_stmt.excluded.last_updated,
                "sample_ids": insert_stmt.excluded.sample_ids,
                "test_ids": insert_stmt.excluded.test_ids,
                "raw_payload": insert_stmt.excluded.raw_payload,
                "fetched_at": func.now(),
            }
            session.execute(insert_stmt.on_conflict_do_update(index_elements=[Batch.id], set_=update_stmt))
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
