"""Routes for operational efficiency analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db_session
from ..schemas.analytics import (
    OrdersFunnelResponse,
    OrdersSlowestResponse,
    OrdersThroughputResponse,
    SamplesCycleTimeResponse,
)
from ..services.analytics import (
    get_orders_funnel,
    get_slowest_orders,
    get_orders_throughput,
    get_samples_cycle_time,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/orders/throughput", response_model=OrdersThroughputResponse)
def orders_throughput(
    date_from: Optional[datetime] = Query(
        None, description="Filter orders created on/after this datetime"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter orders created on/before this datetime"
    ),
    customer_id: Optional[int] = Query(None),
    interval: str = Query(
        "day",
        description="Aggregation interval (day or week)",
        pattern="^(day|week)$",
    ),
    session: Session = Depends(get_db_session),
) -> OrdersThroughputResponse:
    """Return counts of orders created/completed and completion times by interval."""

    return get_orders_throughput(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        interval=interval,
    )


@router.get("/samples/cycle-time", response_model=SamplesCycleTimeResponse)
def samples_cycle_time(
    date_from: Optional[datetime] = Query(
        None, description="Filter samples completed on/after this datetime"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter samples completed on/before this datetime"
    ),
    customer_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    matrix_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    interval: str = Query(
        "day",
        description="Aggregation interval (day or week)",
        pattern="^(day|week)$",
    ),
    session: Session = Depends(get_db_session),
) -> SamplesCycleTimeResponse:
    """Return sample cycle-time statistics grouped by interval and matrix type."""

    return get_samples_cycle_time(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        order_id=order_id,
        matrix_type=matrix_type,
        state=state,
        interval=interval,
    )


@router.get("/orders/funnel", response_model=OrdersFunnelResponse)
def orders_funnel(
    date_from: Optional[datetime] = Query(
        None, description="Filter orders created on/after this datetime"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter orders created on/before this datetime"
    ),
    customer_id: Optional[int] = Query(None),
    session: Session = Depends(get_db_session),
) -> OrdersFunnelResponse:
    """Return funnel counts for order lifecycle stages."""

    return get_orders_funnel(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
    )


@router.get("/orders/slowest", response_model=OrdersSlowestResponse)
def orders_slowest(
    date_from: Optional[datetime] = Query(
        None, description="Filter orders created on/after this datetime"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter orders created on/before this datetime"
    ),
    customer_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of slowest orders to return",
    ),
    session: Session = Depends(get_db_session),
) -> OrdersSlowestResponse:
    """Return the slowest orders ranked by completion time or current age."""

    return get_slowest_orders(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        state=state,
        limit=limit,
    )
