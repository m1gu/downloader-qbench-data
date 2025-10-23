"""Pydantic schemas for analytics endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrdersThroughputPoint(BaseModel):
    period_start: date = Field(..., description="Beginning of the aggregation interval")
    orders_created: int = Field(..., description="Orders created during the interval")
    orders_completed: int = Field(..., description="Orders completed during the interval")
    average_completion_hours: Optional[float] = Field(
        None, description="Average hours from creation to completion for orders completed in the interval"
    )
    median_completion_hours: Optional[float] = Field(
        None, description="Median hours from creation to completion for orders completed in the interval"
    )


class OrdersThroughputTotals(BaseModel):
    orders_created: int
    orders_completed: int
    average_completion_hours: Optional[float]
    median_completion_hours: Optional[float]


class OrdersThroughputResponse(BaseModel):
    interval: str = Field(..., description="Aggregation granularity: day or week")
    points: list[OrdersThroughputPoint]
    totals: OrdersThroughputTotals


class SamplesCycleTimePoint(BaseModel):
    period_start: date
    completed_samples: int
    average_cycle_hours: Optional[float]
    median_cycle_hours: Optional[float]


class SamplesCycleMatrixItem(BaseModel):
    matrix_type: str
    completed_samples: int
    average_cycle_hours: Optional[float]


class SamplesCycleTimeTotals(BaseModel):
    completed_samples: int
    average_cycle_hours: Optional[float]
    median_cycle_hours: Optional[float]


class SamplesCycleTimeResponse(BaseModel):
    interval: str = Field(..., description="Aggregation granularity: day or week")
    points: list[SamplesCycleTimePoint]
    totals: SamplesCycleTimeTotals
    by_matrix_type: list[SamplesCycleMatrixItem]


class OrdersFunnelStage(BaseModel):
    stage: str
    count: int


class OrdersFunnelResponse(BaseModel):
    total_orders: int = Field(..., description="Orders created within the requested range")
    stages: list[OrdersFunnelStage]


class SlowOrderItem(BaseModel):
    order_id: int = Field(..., description="Internal order identifier")
    order_reference: str = Field(..., description="Display-friendly order code")
    customer_name: Optional[str] = Field(None, description="Customer linked to the order")
    state: Optional[str] = Field(None, description="Current order state")
    completion_hours: Optional[float] = Field(
        None,
        description="Hours from order creation to completion. Null when order is not completed.",
    )
    age_hours: float = Field(..., description="Hours since creation up to completion or reference time")
    date_created: Optional[datetime] = Field(None, description="Order creation timestamp")
    date_completed: Optional[datetime] = Field(None, description="Order completion timestamp")


class OrdersSlowestResponse(BaseModel):
    items: list[SlowOrderItem]
