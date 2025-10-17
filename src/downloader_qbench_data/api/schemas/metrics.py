"""Pydantic schemas for metrics endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class SamplesOverviewKPI(BaseModel):
    total_samples: int = Field(..., description="Total samples within the filter scope")
    completed_samples: int = Field(..., description="Samples with completed_date within the range")
    pending_samples: int = Field(..., description="Samples lacking completion state within the range")


class SamplesDistributionItem(BaseModel):
    key: str
    count: int


class SamplesOverviewResponse(BaseModel):
    kpis: SamplesOverviewKPI
    by_state: list[SamplesDistributionItem]
    by_matrix_type: list[SamplesDistributionItem]
    created_vs_completed: list[SamplesDistributionItem]


class TestsOverviewKPI(BaseModel):
    total_tests: int
    completed_tests: int
    pending_tests: int


class TestsDistributionItem(BaseModel):
    key: str
    count: int


class TestsOverviewResponse(BaseModel):
    kpis: TestsOverviewKPI
    by_state: list[TestsDistributionItem]
    by_label: list[TestsDistributionItem]


class TimeSeriesPoint(BaseModel):
    period_start: date
    value: float


class TestsTATMetrics(BaseModel):
    average_hours: float | None
    median_hours: float | None
    p95_hours: float | None
    completed_within_sla: int
    completed_beyond_sla: int


class TestsTATDistributionBucket(BaseModel):
    label: str
    count: int


class TestsTATResponse(BaseModel):
    metrics: TestsTATMetrics
    distribution: list[TestsTATDistributionBucket]
    series: list[TimeSeriesPoint]


class TestsTATBreakdownItem(BaseModel):
    label: str
    average_hours: float | None
    median_hours: float | None
    p95_hours: float | None
    total_tests: int


class TestsTATBreakdownResponse(BaseModel):
    breakdown: list[TestsTATBreakdownItem]


class MetricsFiltersResponse(BaseModel):
    customers: list[dict[str, int | str]]
    sample_states: list[str]
    test_states: list[str]
    last_updated_at: Optional[datetime] = None
