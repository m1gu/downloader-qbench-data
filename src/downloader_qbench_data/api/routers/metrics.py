"""Routes for metrics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db_session
from ..schemas.metrics import (
    MetricsFiltersResponse,
    SamplesOverviewResponse,
    TestsOverviewResponse,
    TestsTATBreakdownResponse,
    TestsTATResponse,
)
from ..services.metrics import (
    get_metrics_filters,
    get_samples_overview,
    get_tests_overview,
    get_tests_tat,
    get_tests_tat_breakdown,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/samples/overview", response_model=SamplesOverviewResponse)
def samples_overview(
    date_from: Optional[datetime] = Query(None, description="Filter samples created after this datetime"),
    date_to: Optional[datetime] = Query(None, description="Filter samples created before this datetime"),
    customer_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    session: Session = Depends(get_db_session),
) -> SamplesOverviewResponse:
    """Return aggregated metrics for samples."""

    return get_samples_overview(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
    )


@router.get("/tests/overview", response_model=TestsOverviewResponse)
def tests_overview(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    customer_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    batch_id: Optional[int] = Query(None),
    session: Session = Depends(get_db_session),
) -> TestsOverviewResponse:
    """Return aggregated metrics for tests."""

    return get_tests_overview(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
        batch_id=batch_id,
    )


@router.get("/tests/tat", response_model=TestsTATResponse)
def tests_tat(
    date_created_from: Optional[datetime] = Query(None),
    date_created_to: Optional[datetime] = Query(None),
    customer_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    group_by: Optional[str] = Query(
        None,
        pattern="^(day|week)$",
        description="Optional grouping interval for time series data",
    ),
    session: Session = Depends(get_db_session),
) -> TestsTATResponse:
    """Return turnaround time metrics for tests."""

    return get_tests_tat(
        session,
        date_created_from=date_created_from,
        date_created_to=date_created_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
        group_by=group_by,
    )


@router.get("/tests/tat-breakdown", response_model=TestsTATBreakdownResponse)
def tests_tat_breakdown(
    date_created_from: Optional[datetime] = Query(None),
    date_created_to: Optional[datetime] = Query(None),
    session: Session = Depends(get_db_session),
) -> TestsTATBreakdownResponse:
    """Return TAT metrics broken down by label."""

    return get_tests_tat_breakdown(
        session,
        date_created_from=date_created_from,
        date_created_to=date_created_to,
    )


@router.get("/common/filters", response_model=MetricsFiltersResponse)
def metrics_filters(
    session: Session = Depends(get_db_session),
) -> MetricsFiltersResponse:
    """Return values for populating dashboard filters."""

    return get_metrics_filters(session)
