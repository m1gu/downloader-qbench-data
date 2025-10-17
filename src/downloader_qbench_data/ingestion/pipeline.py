"""Orchestration helpers to run multiple QBench entity syncs sequentially."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Optional, Sequence

from downloader_qbench_data.config import AppSettings, get_settings
from downloader_qbench_data.ingestion.batches import sync_batches
from downloader_qbench_data.ingestion.customers import sync_customers
from downloader_qbench_data.ingestion.orders import sync_orders
from downloader_qbench_data.ingestion.samples import sync_samples
from downloader_qbench_data.ingestion.tests import sync_tests

LOGGER = logging.getLogger(__name__)

EntityProgressCallback = Callable[[str, int, Optional[int]], None]
EntitySyncCallable = Callable[..., Any]

DEFAULT_SYNC_SEQUENCE: tuple[str, ...] = ("customers", "orders", "samples", "batches", "tests")

_SYNC_HANDLERS: dict[str, EntitySyncCallable] = {
    "customers": sync_customers,
    "orders": sync_orders,
    "samples": sync_samples,
    "batches": sync_batches,
    "tests": sync_tests,
}


@dataclass
class EntitySyncResult:
    """Represents the outcome of syncing a single entity."""

    entity: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    succeeded: bool
    summary: Any | None = None
    error_message: str | None = None


@dataclass
class SyncRunSummary:
    """Aggregated view of a multi-entity sync execution."""

    started_at: datetime
    completed_at: datetime
    succeeded: bool
    results: list[EntitySyncResult] = field(default_factory=list)
    failed_entity: str | None = None
    error_message: str | None = None

    def __bool__(self) -> bool:
        return self.succeeded

    @property
    def total_duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()


class SyncOrchestrationError(RuntimeError):
    """Raised when the orchestration fails on a specific entity."""

    def __init__(self, entity: str, original: Exception) -> None:
        super().__init__(f"Failed syncing '{entity}': {original}")
        self.entity = entity
        self.original = original


def sync_all_entities(
    settings: Optional[AppSettings] = None,
    *,
    entities: Optional[Iterable[str]] = None,
    full_refresh: bool = False,
    page_size: Optional[int] = None,
    progress_callback: Optional[EntityProgressCallback] = None,
    raise_on_error: bool = True,
) -> SyncRunSummary:
    """Synchronise multiple entities sequentially using stored checkpoints.

    Args:
        settings: Optional pre-loaded application settings; falls back to :func:`get_settings`.
        entities: Subset of entity names to run. Defaults to the canonical order defined
            in :data:`DEFAULT_SYNC_SEQUENCE`.
        full_refresh: When ``True`` forces all entities to refresh from scratch.
        page_size: Optional page size override passed through to each entity pipeline.
        progress_callback: Optional callable receiving ``(entity, processed_pages, total_pages)``.
        raise_on_error: When ``True`` re-raises a :class:`SyncOrchestrationError` if any entity fails.

    Returns:
        :class:`SyncRunSummary` detailing the outcome of the run.
    """

    effective_settings = settings or get_settings()
    sequence = _resolve_entity_sequence(entities)
    run_started_at = datetime.utcnow()
    results: list[EntitySyncResult] = []
    failed_entity: str | None = None
    aggregated_error: Exception | None = None

    LOGGER.info(
        "Starting multi-entity sync (entities=%s, full_refresh=%s, page_size=%s)",
        ", ".join(sequence),
        full_refresh,
        page_size,
    )

    for entity in sequence:
        handler = _SYNC_HANDLERS[entity]
        entity_started_at = datetime.utcnow()
        LOGGER.info("Starting sync for entity '%s'", entity)
        try:
            summary = handler(
                effective_settings,
                full_refresh=full_refresh,
                page_size=page_size,
                progress_callback=_wrap_progress_callback(progress_callback, entity),
            )
            entity_completed_at = datetime.utcnow()
            duration = (entity_completed_at - entity_started_at).total_seconds()
            LOGGER.info(
                "Completed sync for entity '%s' in %.2f seconds",
                entity,
                duration,
            )
            results.append(
                EntitySyncResult(
                    entity=entity,
                    started_at=entity_started_at,
                    completed_at=entity_completed_at,
                    duration_seconds=duration,
                    succeeded=True,
                    summary=summary,
                )
            )
        except Exception as exc:  # noqa: BLE001 - orchestrator must catch all
            entity_completed_at = datetime.utcnow()
            duration = (entity_completed_at - entity_started_at).total_seconds()
            LOGGER.exception("Sync for entity '%s' failed after %.2f seconds", entity, duration)
            failed_entity = entity
            aggregated_error = exc
            results.append(
                EntitySyncResult(
                    entity=entity,
                    started_at=entity_started_at,
                    completed_at=entity_completed_at,
                    duration_seconds=duration,
                    succeeded=False,
                    summary=None,
                    error_message=str(exc),
                )
            )
            break

    run_completed_at = datetime.utcnow()
    succeeded = failed_entity is None and len(results) == len(sequence)
    summary = SyncRunSummary(
        started_at=run_started_at,
        completed_at=run_completed_at,
        succeeded=succeeded,
        results=results,
        failed_entity=failed_entity,
        error_message=str(aggregated_error) if aggregated_error else None,
    )

    if aggregated_error and raise_on_error:
        raise SyncOrchestrationError(failed_entity or "unknown", aggregated_error) from aggregated_error

    if succeeded:
        LOGGER.info("Multi-entity sync completed successfully in %.2f seconds", summary.total_duration_seconds)
    else:
        LOGGER.warning(
            "Multi-entity sync finished with failure on '%s' after %.2f seconds",
            failed_entity,
            summary.total_duration_seconds,
        )
    return summary


def _wrap_progress_callback(
    callback: Optional[EntityProgressCallback],
    entity: str,
) -> Optional[Callable[[int, Optional[int]], None]]:
    if not callback:
        return None

    def _progress(page_count: int, total_pages: Optional[int]) -> None:
        callback(entity, page_count, total_pages)

    return _progress


def _resolve_entity_sequence(entities: Optional[Iterable[str]]) -> Sequence[str]:
    if entities is None:
        return DEFAULT_SYNC_SEQUENCE
    normalized = []
    for entity in entities:
        if entity not in _SYNC_HANDLERS:
            raise ValueError(f"Unknown entity '{entity}'. Supported values: {', '.join(sorted(_SYNC_HANDLERS))}")
        normalized.append(entity)
    # Ensure specified order is preserved without duplicates
    seen: set[str] = set()
    ordered = []
    for entity in normalized:
        if entity in seen:
            continue
        ordered.append(entity)
        seen.add(entity)
    return tuple(ordered)

