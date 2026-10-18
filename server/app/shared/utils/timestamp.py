from datetime import UTC, datetime, timedelta


def get_current_timestamp(
    *,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Returns a UTC datetime object with an optional time offset."""
    now = datetime.now(UTC)
    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return now + delta
