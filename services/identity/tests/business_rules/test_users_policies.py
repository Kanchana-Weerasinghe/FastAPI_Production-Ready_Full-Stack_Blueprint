"""UserAccount policies: decisions that need facts from outside the entity. No database."""

from datetime import datetime, timedelta

import pytest

from app.modules.users.domain.policies import lockout_expiry
from tests.business_rules.users_builders import NOW


@pytest.mark.br("BR-08", "TC-08-1")
def test_br_08_lockout_expiry_adds_the_configured_duration() -> None:
    assert lockout_expiry(now=NOW, lockout_minutes=15) == NOW + timedelta(minutes=15)


@pytest.mark.br("BR-08", "TC-08-2")
def test_br_08_lockout_expiry_requires_timezone_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        lockout_expiry(now=datetime(2026, 1, 1), lockout_minutes=15)
