"""Routes for entity detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ..dependencies import get_db_session
from ..schemas.entities import SampleDetailResponse, TestDetailResponse
from ..services import entities as entities_service

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/samples/{sample_id}", response_model=SampleDetailResponse)
def get_sample_detail(
    sample_id: int = Path(..., description="Identifier of the sample"),
    session: Session = Depends(get_db_session),
) -> SampleDetailResponse:
    """Return details for a specific sample."""

    result = entities_service.get_sample_detail(session, sample_id=sample_id)
    if not result:
        raise HTTPException(status_code=404, detail="Sample not found")
    return result


@router.get("/tests/{test_id}", response_model=TestDetailResponse)
def get_test_detail(
    test_id: int = Path(..., description="Identifier of the test"),
    session: Session = Depends(get_db_session),
) -> TestDetailResponse:
    """Return details for a specific test."""

    result = entities_service.get_test_detail(session, test_id=test_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test not found")
    return result
