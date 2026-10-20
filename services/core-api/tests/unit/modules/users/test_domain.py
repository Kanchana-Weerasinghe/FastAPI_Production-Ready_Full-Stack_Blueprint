from datetime import UTC, datetime, timedelta

import pytest

from app.modules.users.domain.entities import AccountAccess


def test_account_access_is_locked_until_expiry() -> None:
    """Verify only future lock expirations block sign-in."""
    now = datetime.now(UTC)

    assert AccountAccess(now + timedelta(minutes=5)).is_locked(now)
    assert not AccountAccess(now - timedelta(seconds=1)).is_locked(now)
    assert not AccountAccess(None).is_locked(now)


def test_account_access_requires_timezone_aware_clock() -> None:
    """Verify naive datetimes are rejected rather than compared ambiguously."""
    with pytest.raises(ValueError, match="timezone-aware"):
        AccountAccess(None).is_locked(datetime.now())
