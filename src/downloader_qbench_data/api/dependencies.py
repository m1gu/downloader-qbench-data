"""Shared dependency providers for the FastAPI layer."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from downloader_qbench_data.config import AppSettings, get_settings
from downloader_qbench_data.storage import get_session_factory


def get_app_settings() -> AppSettings:
    """Return cached application settings."""

    return get_settings()


def get_db_session(settings: AppSettings = Depends(get_app_settings)) -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session scoped to the request lifecycle."""

    session_factory = get_session_factory(settings)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()
