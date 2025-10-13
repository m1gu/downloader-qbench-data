"""Shared helpers for ingestion routines."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Optional

LOGGER = logging.getLogger(__name__)

_DATETIME_FORMATS = [
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]


def parse_qbench_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse the date/time formats commonly returned by QBench.

    Returns ``None`` when the value is empty or the format is unknown.
    """

    if not value:
        return None

    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    if value.isdigit():
        try:
            return datetime.fromtimestamp(int(value))
        except (OverflowError, ValueError):
            LOGGER.warning("Could not parse timestamp '%s'", value)
            return None

    LOGGER.warning("Unknown QBench datetime format: %s", value)
    return None


def safe_int(value: Optional[int | str]) -> Optional[int]:
    """Convert a value to ``int`` when possible."""

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        LOGGER.warning("Could not cast value '%s' to int", value)
        return None


def ensure_int_list(values: Optional[Iterable[int | str]]) -> list[int]:
    """Return a list of integers from an iterable, skipping invalid entries."""

    if not values:
        return []
    result: list[int] = []
    for value in values:
        converted = safe_int(value)
        if converted is not None:
            result.append(converted)
    return result
