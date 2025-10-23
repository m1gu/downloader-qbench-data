"""Service helpers for analytics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from downloader_qbench_data.storage import Customer, Order, Sample
from ..schemas.analytics import (
    OrdersFunnelResponse,
    OrdersFunnelStage,
    OrdersSlowestResponse,
    OrdersThroughputPoint,
    OrdersThroughputResponse,
    OrdersThroughputTotals,
    SlowOrderItem,
    SamplesCycleMatrixItem,
    SamplesCycleTimePoint,
    SamplesCycleTimeResponse,
    SamplesCycleTimeTotals,
)
from .metrics import _daterange_conditions  # reuse date range helper for consistency

_VALID_INTERVALS = {"day", "week"}


def _normalise_interval(interval: Optional[str]) -> str:
    if not interval:
        return "day"
    interval_lower = interval.lower()
    if interval_lower not in _VALID_INTERVALS:
        raise ValueError(f"Unsupported interval '{interval}'. Allowed values: {sorted(_VALID_INTERVALS)}")
    return interval_lower


def _epoch_hours(expr) -> any:
    return func.extract("epoch", expr) / 3600.0


def _convert_period(period_value) -> datetime.date:
    if period_value is None:
        raise ValueError("Aggregation period cannot be null")
    if hasattr(period_value, "date"):
        return period_value.date()
    return period_value  # Already a date


def get_orders_throughput(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    interval: Optional[str] = "day",
) -> OrdersThroughputResponse:
    """Aggregate orders created/completed counts and completion times."""

    interval_value = _normalise_interval(interval)

    created_conditions = _daterange_conditions(Order.date_created, date_from, date_to)
    completed_conditions = _daterange_conditions(Order.date_completed, date_from, date_to)
    if customer_id is not None:
        created_conditions.append(Order.customer_account_id == customer_id)
        completed_conditions.append(Order.customer_account_id == customer_id)

    created_stmt = (
        select(
            func.date_trunc(interval_value, Order.date_created).label("period"),
            func.count().label("created_count"),
        )
        .where(Order.date_created.isnot(None), *created_conditions)
        .group_by("period")
        .order_by("period")
    )

    duration_expr = _epoch_hours(Order.date_completed - Order.date_created)
    completed_stmt = (
        select(
            func.date_trunc(interval_value, Order.date_completed).label("period"),
            func.count().label("completed_count"),
            func.avg(duration_expr).label("avg_hours"),
            func.percentile_cont(0.5).within_group(duration_expr).label("median_hours"),
        )
        .where(Order.date_completed.isnot(None), Order.date_created.isnot(None), *completed_conditions)
        .group_by("period")
        .order_by("period")
    )

    created_map: Dict[datetime.date, int] = {}
    for row in session.execute(created_stmt):
        period = _convert_period(row.period)
        created_map[period] = int(row.created_count or 0)

    completed_map: Dict[datetime.date, Tuple[int, Optional[float], Optional[float]]] = {}
    for row in session.execute(completed_stmt):
        period = _convert_period(row.period)
        avg_hours = float(row.avg_hours) if row.avg_hours is not None else None
        median_hours = float(row.median_hours) if row.median_hours is not None else None
        completed_map[period] = (int(row.completed_count or 0), avg_hours, median_hours)

    periods = sorted(set(created_map) | set(completed_map))
    points: list[OrdersThroughputPoint] = []
    for period in periods:
        completed_count, avg_hours, median_hours = completed_map.get(period, (0, None, None))
        points.append(
            OrdersThroughputPoint(
                period_start=period,
                orders_created=created_map.get(period, 0),
                orders_completed=completed_count,
                average_completion_hours=avg_hours,
                median_completion_hours=median_hours,
            )
        )

    # Totals
    total_created = sum(created_map.values())
    total_completed = sum(value[0] for value in completed_map.values())
    total_duration_stmt = (
        select(
            func.count().label("completed"),
            func.avg(duration_expr).label("avg_hours"),
            func.percentile_cont(0.5).within_group(duration_expr).label("median_hours"),
        )
        .where(Order.date_completed.isnot(None), Order.date_created.isnot(None), *completed_conditions)
    )
    total_row = session.execute(total_duration_stmt).one()
    total_avg = float(total_row.avg_hours) if total_row.avg_hours is not None else None
    total_median = float(total_row.median_hours) if total_row.median_hours is not None else None

    response = OrdersThroughputResponse(
        interval=interval_value,
        points=points,
        totals=OrdersThroughputTotals(
            orders_created=total_created,
            orders_completed=total_completed,
            average_completion_hours=total_avg,
            median_completion_hours=total_median,
        ),
    )
    return response


def _sample_cycle_conditions(
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    customer_id: Optional[int],
    order_id: Optional[int],
    matrix_type: Optional[str],
    state: Optional[str],
) -> Tuple[list, bool]:
    conditions = _daterange_conditions(Sample.completed_date, date_from, date_to)
    join_order = False
    if customer_id is not None:
        join_order = True
        conditions.append(Order.customer_account_id == customer_id)
    if order_id is not None:
        conditions.append(Sample.order_id == order_id)
    if matrix_type:
        conditions.append(Sample.matrix_type == matrix_type)
    if state:
        conditions.append(Sample.state == state)
    return conditions, join_order


def get_samples_cycle_time(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    order_id: Optional[int] = None,
    matrix_type: Optional[str] = None,
    state: Optional[str] = None,
    interval: Optional[str] = "day",
) -> SamplesCycleTimeResponse:
    """Return cycle time metrics for samples."""

    interval_value = _normalise_interval(interval)
    conditions, join_order = _sample_cycle_conditions(
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        matrix_type=matrix_type,
        state=state,
    )

    stmt = (
        select(
            func.date_trunc(interval_value, Sample.completed_date).label("period"),
            func.count().label("completed_samples"),
            func.avg(_epoch_hours(Sample.completed_date - Sample.date_created)).label("avg_hours"),
            func.percentile_cont(0.5).within_group(_epoch_hours(Sample.completed_date - Sample.date_created)).label(
                "median_hours"
            ),
        )
        .where(
            Sample.completed_date.isnot(None),
            Sample.date_created.isnot(None),
            *conditions,
        )
        .group_by("period")
        .order_by("period")
    )
    if join_order:
        stmt = stmt.join(Order, Order.id == Sample.order_id)

    points: list[SamplesCycleTimePoint] = []
    result = session.execute(stmt)
    for row in result:
        period = _convert_period(row.period)
        avg_hours = float(row.avg_hours) if row.avg_hours is not None else None
        median_hours = float(row.median_hours) if row.median_hours is not None else None
        points.append(
            SamplesCycleTimePoint(
                period_start=period,
                completed_samples=int(row.completed_samples or 0),
                average_cycle_hours=avg_hours,
                median_cycle_hours=median_hours,
            )
        )

    totals_stmt = (
        select(
            func.count().label("completed_samples"),
            func.avg(_epoch_hours(Sample.completed_date - Sample.date_created)).label("avg_hours"),
            func.percentile_cont(0.5).within_group(_epoch_hours(Sample.completed_date - Sample.date_created)).label(
                "median_hours"
            ),
        )
        .where(
            Sample.completed_date.isnot(None),
            Sample.date_created.isnot(None),
            *conditions,
        )
    )
    if join_order:
        totals_stmt = totals_stmt.join(Order, Order.id == Sample.order_id)
    totals_row = session.execute(totals_stmt).one()
    totals = SamplesCycleTimeTotals(
        completed_samples=int(totals_row.completed_samples or 0),
        average_cycle_hours=float(totals_row.avg_hours) if totals_row.avg_hours is not None else None,
        median_cycle_hours=float(totals_row.median_hours) if totals_row.median_hours is not None else None,
    )

    matrix_stmt = (
        select(
            func.coalesce(Sample.matrix_type, "Unknown").label("matrix_type"),
            func.count().label("completed_samples"),
            func.avg(_epoch_hours(Sample.completed_date - Sample.date_created)).label("avg_hours"),
        )
        .where(
            Sample.completed_date.isnot(None),
            Sample.date_created.isnot(None),
            *conditions,
        )
        .group_by("matrix_type")
        .order_by("matrix_type")
    )
    if join_order:
        matrix_stmt = matrix_stmt.join(Order, Order.id == Sample.order_id)

    by_matrix: list[SamplesCycleMatrixItem] = []
    for row in session.execute(matrix_stmt):
        avg_hours = float(row.avg_hours) if row.avg_hours is not None else None
        by_matrix.append(
            SamplesCycleMatrixItem(
                matrix_type=row.matrix_type,
                completed_samples=int(row.completed_samples or 0),
                average_cycle_hours=avg_hours,
            )
        )

    return SamplesCycleTimeResponse(
        interval=interval_value,
        points=points,
        totals=totals,
        by_matrix_type=by_matrix,
    )


def get_orders_funnel(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
) -> OrdersFunnelResponse:
    """Return counts for each stage of the order lifecycle."""

    created_conditions = _daterange_conditions(Order.date_created, date_from, date_to)
    received_conditions = _daterange_conditions(Order.date_received, date_from, date_to)
    completed_conditions = _daterange_conditions(Order.date_completed, date_from, date_to)
    reported_conditions = _daterange_conditions(Order.date_order_reported, date_from, date_to)

    if customer_id is not None:
        created_conditions.append(Order.customer_account_id == customer_id)
        received_conditions.append(Order.customer_account_id == customer_id)
        completed_conditions.append(Order.customer_account_id == customer_id)
        reported_conditions.append(Order.customer_account_id == customer_id)

    def _count(column_conditions: Iterable, column_is_not_null) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(column_is_not_null, *column_conditions)
        )
        return int(session.execute(stmt).scalar_one() or 0)

    total_created = _count(created_conditions, Order.date_created.isnot(None))
    received = _count(received_conditions, Order.date_received.isnot(None))
    completed = _count(completed_conditions, Order.date_completed.isnot(None))
    reported = _count(reported_conditions, Order.date_order_reported.isnot(None))

    on_hold_conditions = list(created_conditions)
    on_hold_conditions.append(Order.state == "ON HOLD")
    on_hold = _count(on_hold_conditions, Order.date_created.isnot(None))

    stages = [
        OrdersFunnelStage(stage="created", count=total_created),
        OrdersFunnelStage(stage="received", count=received),
        OrdersFunnelStage(stage="completed", count=completed),
        OrdersFunnelStage(stage="reported", count=reported),
        OrdersFunnelStage(stage="on_hold", count=on_hold),
    ]

    return OrdersFunnelResponse(total_orders=total_created, stages=stages)


def get_slowest_orders(
    session: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    state: Optional[str] = None,
    limit: int = 10,
) -> OrdersSlowestResponse:
    """Return slowest orders by completion time or current age."""

    effective_limit = max(1, min(limit, 100))

    conditions = _daterange_conditions(Order.date_created, date_from, date_to)
    conditions.append(Order.date_created.isnot(None))
    if customer_id is not None:
        conditions.append(Order.customer_account_id == customer_id)
    if state:
        conditions.append(Order.state == state)

    reference_expr = literal(date_to) if date_to else func.now()
    completion_expr = _epoch_hours(Order.date_completed - Order.date_created)
    age_expr = func.greatest(_epoch_hours(reference_expr - Order.date_created), literal(0.0))
    sort_key = func.coalesce(completion_expr, age_expr)

    stmt = (
        select(
            Order.id.label("order_id"),
            func.coalesce(Order.custom_formatted_id, func.concat("order-", Order.id)).label("order_reference"),
            Customer.name.label("customer_name"),
            Order.state.label("state"),
            Order.date_created.label("date_created"),
            Order.date_completed.label("date_completed"),
            completion_expr.label("completion_hours"),
            age_expr.label("age_hours"),
        )
        .select_from(Order)
        .join(Customer, Customer.id == Order.customer_account_id, isouter=True)
        .where(*conditions)
        .order_by(sort_key.desc(), Order.date_created.desc())
        .limit(effective_limit)
    )

    rows = session.execute(stmt)
    items: list[SlowOrderItem] = []
    for row in rows:
        completion_hours = float(row.completion_hours) if row.completion_hours is not None else None
        age_hours = float(row.age_hours) if row.age_hours is not None else 0.0
        items.append(
            SlowOrderItem(
                order_id=row.order_id,
                order_reference=row.order_reference,
                customer_name=row.customer_name,
                state=row.state,
                completion_hours=completion_hours,
                age_hours=age_hours,
                date_created=row.date_created,
                date_completed=row.date_completed,
            )
        )

    return OrdersSlowestResponse(items=items)
