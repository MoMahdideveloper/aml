"""UTC clock helpers for Track A.

DB DateTime columns store **naive UTC**. Use ``utc_now_naive()`` at the
persistence and comparison boundary. See ``tasks/datetime_compatibility.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """Naive UTC for SQLAlchemy DateTime columns and naive comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)
