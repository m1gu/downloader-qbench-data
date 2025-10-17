"""Data access helpers for sample/test detail endpoints."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from downloader_qbench_data.storage import Batch, Order, Sample, Test
from ..schemas.entities import SampleDetailResponse, TestDetailResponse


def get_sample_detail(session: Session, *, sample_id: int) -> Optional[SampleDetailResponse]:
    stmt = (
        select(Sample, Order)
        .join(Order, Sample.order_id == Order.id)
        .where(Sample.id == sample_id)
    )
    row = session.execute(stmt).one_or_none()
    if not row:
        return None
    sample, order = row

    batch_rows = session.execute(
        select(Batch.id, Batch.display_name).where(Batch.id.in_(sample.batch_ids))
    ).all() if sample.batch_ids else []

    return SampleDetailResponse(
        id=sample.id,
        sample_name=sample.sample_name,
        custom_formatted_id=sample.custom_formatted_id,
        order_id=sample.order_id,
        has_report=sample.has_report,
        batch_ids=sample.batch_ids or [],
        completed_date=sample.completed_date,
        date_created=sample.date_created,
        start_date=sample.start_date,
        matrix_type=sample.matrix_type,
        state=sample.state,
        test_count=sample.test_count,
        raw_payload=sample.raw_payload,
        order={
            "id": order.id,
            "custom_formatted_id": order.custom_formatted_id,
            "state": order.state,
        },
        batches=[{"id": bid, "display_name": name} for bid, name in batch_rows],
    )


def get_test_detail(session: Session, *, test_id: int) -> Optional[TestDetailResponse]:
    stmt = (
        select(Test, Sample)
        .join(Sample, Sample.id == Test.sample_id)
        .where(Test.id == test_id)
    )
    row = session.execute(stmt).one_or_none()
    if not row:
        return None
    test, sample = row

    batch_rows = session.execute(
        select(Batch.id, Batch.display_name).where(Batch.id.in_(test.batch_ids))
    ).all() if test.batch_ids else []

    return TestDetailResponse(
        id=test.id,
        sample_id=test.sample_id,
        batch_ids=test.batch_ids or [],
        date_created=test.date_created,
        state=test.state,
        has_report=test.has_report,
        report_completed_date=test.report_completed_date,
        label_abbr=test.label_abbr,
        title=test.title,
        worksheet_raw=test.worksheet_raw,
        raw_payload=test.raw_payload,
        sample={
            "id": sample.id,
            "sample_name": sample.sample_name,
            "state": sample.state,
        },
        batches=[{"id": bid, "display_name": name} for bid, name in batch_rows],
    )
