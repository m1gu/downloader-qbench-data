"""Pydantic schemas for entity detail endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SampleDetailResponse(BaseModel):
    id: int
    sample_name: Optional[str]
    custom_formatted_id: Optional[str]
    order_id: int
    has_report: bool
    batch_ids: list[int]
    completed_date: Optional[datetime]
    date_created: Optional[datetime]
    start_date: Optional[datetime]
    matrix_type: Optional[str]
    state: Optional[str]
    test_count: Optional[int]
    raw_payload: dict[str, Any]
    order: Optional[dict[str, Any]] = Field(None, description="Simplified order information")
    batches: list[dict[str, Any]] = Field(default_factory=list)


class TestDetailResponse(BaseModel):
    id: int
    sample_id: int
    batch_ids: list[int]
    date_created: Optional[datetime]
    state: Optional[str]
    has_report: bool
    report_completed_date: Optional[datetime]
    label_abbr: Optional[str]
    title: Optional[str]
    worksheet_raw: Optional[dict[str, Any]]
    raw_payload: dict[str, Any]
    sample: Optional[dict[str, Any]] = None
    batches: list[dict[str, Any]] = Field(default_factory=list)
