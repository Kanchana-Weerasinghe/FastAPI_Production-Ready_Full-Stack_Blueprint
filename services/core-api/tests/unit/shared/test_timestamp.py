from datetime import UTC, datetime

from app.shared.utils.timestamp import get_current_timestamp


def test_get_current_timestamp_default() -> None:
    """Test that get_current_timestamp returns the current time in UTC when no arguments are passed."""
    ts = get_current_timestamp()
    now = datetime.now(UTC)
    difference = abs((ts - now).total_seconds())
    assert difference < 2.0


def test_get_current_timestamp_offset() -> None:
    """Test that get_current_timestamp correctly applies the specified time offsets."""
    ts = get_current_timestamp(days=1, hours=2, minutes=-30)
    now = datetime.now(UTC)
    expected_difference_seconds = 24 * 3600 + 2 * 3600 - 30 * 60
    actual_difference = (ts - now).total_seconds()
    assert abs(actual_difference - expected_difference_seconds) < 2.0
