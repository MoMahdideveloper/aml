"""Unit tests for UTC clock helpers."""

from datetime import UTC, datetime, timezone

from utils.time_utc import utc_now, utc_now_naive


def test_utc_now_is_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(now)


def test_utc_now_naive_has_no_tzinfo():
    now = utc_now_naive()
    assert now.tzinfo is None
    # Should be close to aware UTC wall clock
    aware = datetime.now(UTC).replace(tzinfo=None)
    assert abs((now - aware).total_seconds()) < 2
