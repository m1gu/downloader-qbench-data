"""Query helpers for metrics endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import mean, median
from typing import DefaultDict, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from downloader_qbench_data.storage import Customer, Order, Sample, Test
from ..schemas.metrics import (
    MetricsFiltersResponse,
    SamplesDistributionItem,
    SamplesOverviewKPI,
    SamplesOverviewResponse,
    TestsDistributionItem,
    TestsOverviewKPI,
    TestsOverviewResponse,
    TestsTATBreakdownItem,
    TestsTATBreakdownResponse,
    TestsTATDistributionBucket,
    TestsTATMetrics,
    TestsTATResponse,
    TimeSeriesPoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _daterange_conditions(column, start: Optional[datetime], end: Optional[datetime]) -> list:
    conditions = []
    if start:
        conditions.append(column >= start)
    if end:
        conditions.append(column <= end)
    return conditions


def _apply_sample_filters(
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    customer_id: Optional[int],
    order_id: Optional[int],
    state: Optional[str],
):
    conditions = _daterange_conditions(Sample.date_created, date_from, date_to)
    join_order = False
    if customer_id is not None:
        conditions.append(Order.customer_account_id == customer_id)
        join_order = True
    if order_id is not None:
        conditions.append(Sample.order_id == order_id)
    if state:
        conditions.append(Sample.state == state)
    return conditions, join_order


def _apply_test_filters(
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    customer_id: Optional[int],
    order_id: Optional[int],
    state: Optional[str],
    batch_id: Optional[int],
):
    conditions = _daterange_conditions(Test.date_created, date_from, date_to)
    join_sample = False
    join_order = False
    if customer_id is not None:
        join_sample = True
        join_order = True
        conditions.append(Order.customer_account_id == customer_id)
    if order_id is not None:
        join_sample = True
        conditions.append(Sample.order_id == order_id)
    if state:
        conditions.append(Test.state == state)
    if batch_id is not None:
        conditions.append(Test.batch_ids.contains([batch_id]))
    return conditions, join_sample, join_order


def _count_with_filters(
    session: Session,
    model,
    *,
    conditions: list,
    join_order: bool = False,
    join_sample: bool = False,
):
    stmt = select(func.count()).select_from(model)
    if model is Sample and join_order:
        stmt = stmt.join(Order, Sample.order_id == Order.id)
    elif model is Test:
        if join_sample:
            stmt = stmt.join(Sample, Sample.id == Test.sample_id)
        if join_order:
            stmt = stmt.join(Order, Sample.order_id == Order.id)
    stmt = stmt.where(*conditions)
    return session.execute(stmt).scalar_one()


def _aggregate_counts(
    session: Session,
    column,
    model,
    *,
    conditions: list,
    join_order: bool = False,
    join_sample: bool = False,
):
    stmt = select(column, func.count()).select_from(model)
    if model is Sample and join_order:
        stmt = stmt.join(Order, Sample.order_id == Order.id)
    elif model is Test:
        if join_sample:
            stmt = stmt.join(Sample, Sample.id == Test.sample_id)
        if join_order:
            stmt = stmt.join(Order, Sample.order_id == Order.id)
    stmt = stmt.where(*conditions).group_by(column).order_by(func.count().desc())
    return [(value or "unknown", count) for value, count in session.execute(stmt)]


# ---------------------------------------------------------------------------
# Samples overview
# ---------------------------------------------------------------------------


def get_samples_overview(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    order_id: Optional[int] = None,
    state: Optional[str] = None,
) -> SamplesOverviewResponse:
    conditions, join_order = _apply_sample_filters(
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
    )

    total_samples = _count_with_filters(
        session,
        Sample,
        conditions=conditions,
        join_order=join_order,
    )

    completed_conditions = list(conditions) + [Sample.completed_date.is_not(None)]
    completed_samples = _count_with_filters(
        session,
        Sample,
        conditions=completed_conditions,
        join_order=join_order,
    )

    pending_samples = total_samples - completed_samples

    by_state = [
        SamplesDistributionItem(key=value, count=count)
        for value, count in _aggregate_counts(
            session,
            Sample.state,
            Sample,
            conditions=conditions,
            join_order=join_order,
        )
    ]

    by_matrix_type = [
        SamplesDistributionItem(key=value, count=count)
        for value, count in _aggregate_counts(
            session,
            Sample.matrix_type,
            Sample,
            conditions=conditions,
            join_order=join_order,
        )
    ]

    created_vs_completed = [
        SamplesDistributionItem(key="created", count=total_samples),
        SamplesDistributionItem(key="completed", count=completed_samples),
    ]

    return SamplesOverviewResponse(
        kpis=SamplesOverviewKPI(
            total_samples=total_samples,
            completed_samples=completed_samples,
            pending_samples=pending_samples,
        ),
        by_state=by_state,
        by_matrix_type=by_matrix_type,
        created_vs_completed=created_vs_completed,
    )


# ---------------------------------------------------------------------------
# Tests overview
# ---------------------------------------------------------------------------


def get_tests_overview(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    order_id: Optional[int] = None,
    state: Optional[str] = None,
    batch_id: Optional[int] = None,
) -> TestsOverviewResponse:
    conditions, join_sample, join_order = _apply_test_filters(
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
        batch_id=batch_id,
    )

    total_tests = _count_with_filters(
        session,
        Test,
        conditions=conditions,
        join_sample=join_sample,
        join_order=join_order,
    )

    completed_conditions = list(conditions) + [Test.report_completed_date.is_not(None)]
    completed_tests = _count_with_filters(
        session,
        Test,
        conditions=completed_conditions,
        join_sample=join_sample,
        join_order=join_order,
    )
    pending_tests = total_tests - completed_tests

    by_state = [
        TestsDistributionItem(key=value, count=count)
        for value, count in _aggregate_counts(
            session,
            Test.state,
            Test,
            conditions=conditions,
            join_sample=join_sample,
            join_order=join_order,
        )
    ]

    by_label = [
        TestsDistributionItem(key=value, count=count)
        for value, count in _aggregate_counts(
            session,
            Test.label_abbr,
            Test,
            conditions=conditions,
            join_sample=join_sample,
            join_order=join_order,
        )
    ]

    return TestsOverviewResponse(
        kpis=TestsOverviewKPI(
            total_tests=total_tests,
            completed_tests=completed_tests,
            pending_tests=pending_tests,
        ),
        by_state=by_state,
        by_label=by_label,
    )


# ---------------------------------------------------------------------------
# Tests TAT
# ---------------------------------------------------------------------------


def get_tests_tat(
    session: Session,
    *,
    date_created_from: Optional[datetime] = None,
    date_created_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    order_id: Optional[int] = None,
    state: Optional[str] = None,
    group_by: Optional[str] = None,
) -> TestsTATResponse:
    conditions, join_sample, join_order = _apply_test_filters(
        date_from=date_created_from,
        date_to=date_created_to,
        customer_id=customer_id,
        order_id=order_id,
        state=state,
        batch_id=None,
    )
    conditions.append(Test.report_completed_date.is_not(None))

    stmt = select(Test.date_created, Test.report_completed_date).select_from(Test)
    if join_sample:
        stmt = stmt.join(Sample, Sample.id == Test.sample_id)
    if join_order:
        stmt = stmt.join(Order, Sample.order_id == Order.id)
    stmt = stmt.where(*conditions)

    tat_values: list[float] = []
    series_acc: DefaultDict[date, list[float]] = defaultdict(list)
    for created_at, completed_at in session.execute(stmt):
        if not created_at or not completed_at:
            continue
        tat_hours = (completed_at - created_at).total_seconds() / 3600.0
        tat_values.append(tat_hours)

        if group_by == "day":
            period = created_at.date()
        elif group_by == "week":
            iso_year, iso_week, _ = created_at.isocalendar()
            period = date.fromisocalendar(iso_year, iso_week, 1)
        else:
            period = None
        if period:
            series_acc[period].append(tat_hours)

    metrics = _compute_tat_metrics(tat_values)
    distribution = _make_distribution(tat_values)
    series = [
        TimeSeriesPoint(period_start=period, value=mean(values))
        for period, values in sorted(series_acc.items(), key=lambda item: item[0])
    ]

    return TestsTATResponse(
        metrics=metrics,
        distribution=distribution,
        series=series,
    )


def _compute_tat_metrics(values: Iterable[float]) -> TestsTATMetrics:
    values = [value for value in values if value is not None]
    if not values:
        return TestsTATMetrics(
            average_hours=None,
            median_hours=None,
            p95_hours=None,
            completed_within_sla=0,
            completed_beyond_sla=0,
        )

    sorted_values = sorted(values)
    avg = mean(sorted_values)
    med = median(sorted_values)
    p95_index = max(0, min(int(len(sorted_values) * 0.95) - 1, len(sorted_values) - 1))
    p95 = sorted_values[p95_index]

    within_sla = sum(1 for value in sorted_values if value <= 48)
    beyond_sla = len(sorted_values) - within_sla

    return TestsTATMetrics(
        average_hours=avg,
        median_hours=med,
        p95_hours=p95,
        completed_within_sla=within_sla,
        completed_beyond_sla=beyond_sla,
    )


def _make_distribution(values: Iterable[float]) -> list[TestsTATDistributionBucket]:
    buckets = [
        ("0-24h", 0, 24),
        ("24-48h", 24, 48),
        ("48-72h", 48, 72),
        ("72-168h", 72, 168),
        (">168h", 168, None),
    ]
    counts = {label: 0 for label, _, _ in buckets}
    for value in values:
        if value is None:
            continue
        for label, min_hours, max_hours in buckets:
            if value >= min_hours and (max_hours is None or value < max_hours):
                counts[label] += 1
                break
    return [
        TestsTATDistributionBucket(label=label, count=counts[label])
        for label, _, _ in buckets
    ]


# ---------------------------------------------------------------------------
# Tests TAT breakdown
# ---------------------------------------------------------------------------


def get_tests_tat_breakdown(
    session: Session,
    *,
    date_created_from: Optional[datetime] = None,
    date_created_to: Optional[datetime] = None,
) -> TestsTATBreakdownResponse:
    conditions, join_sample, join_order = _apply_test_filters(
        date_from=date_created_from,
        date_to=date_created_to,
        customer_id=None,
        order_id=None,
        state=None,
        batch_id=None,
    )
    conditions.append(Test.report_completed_date.is_not(None))

    stmt = select(Test.label_abbr, Test.date_created, Test.report_completed_date).select_from(Test)
    if join_sample:
        stmt = stmt.join(Sample, Sample.id == Test.sample_id)
    if join_order:
        stmt = stmt.join(Order, Sample.order_id == Order.id)
    stmt = stmt.where(*conditions)

    grouped: DefaultDict[str, list[float]] = defaultdict(list)
    for label, created_at, completed_at in session.execute(stmt):
        if not created_at or not completed_at:
            continue
        tat_hours = (completed_at - created_at).total_seconds() / 3600.0
        grouped[label or "unknown"].append(tat_hours)

    breakdown = [
        TestsTATBreakdownItem(
            label=label,
            average_hours=mean(values),
            median_hours=median(values),
            p95_hours=_compute_p95(values),
            total_tests=len(values),
        )
        for label, values in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)
    ]
    return TestsTATBreakdownResponse(breakdown=breakdown)


def _compute_p95(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, min(int(len(sorted_values) * 0.95) - 1, len(sorted_values) - 1))
    return sorted_values[index]


# ---------------------------------------------------------------------------
# Filters endpoint
# ---------------------------------------------------------------------------


def get_metrics_filters(session: Session) -> MetricsFiltersResponse:
    customers = [
        {"id": cid, "name": name}
        for cid, name in session.execute(select(Customer.id, Customer.name).order_by(Customer.name))
    ]
    sample_states = sorted(
        {
            state
            for (state,) in session.execute(select(func.distinct(Sample.state)))
            if state
        }
    )
    test_states = sorted(
        {
            state
            for (state,) in session.execute(select(func.distinct(Test.state)))
            if state
        }
    )
    last_updated_at = session.execute(select(func.max(Test.fetched_at))).scalar_one_or_none()
    return MetricsFiltersResponse(
        customers=customers,
        sample_states=sample_states,
        test_states=test_states,
        last_updated_at=last_updated_at,
    )
