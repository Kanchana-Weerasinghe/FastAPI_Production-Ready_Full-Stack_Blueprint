"""Business rules of the users domain, tested without a database or framework."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.users.domain.entities import UserAccount
from app.modules.users.domain.exceptions import (
    InvalidEmailAddress,
    InvalidPasswordHash,
    InvalidUsername,
    MfaAlreadyEnabled,
    MfaNotStarted,
)
from app.modules.users.domain.policies import lockout_expiry
from app.modules.users.domain.value_objects import EmailAddress, Username

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _account(**overrides: object) -> UserAccount:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "email": EmailAddress("ada@example.com"),
        "username": Username("ADA42"),
        "password_hash": "hash",
        "role": "user",
        "token_version": 0,
        "email_verified_at": None,
        "failed_login_attempts": 0,
        "locked_until": None,
        "mfa_secret_encrypted": None,
        "mfa_enabled_at": None,
        "created_at": NOW,
        "is_active": True,
        "is_deleted": False,
    }
    values.update(overrides)
    return UserAccount(**values)  # type: ignore[arg-type]


# --- Value objects --------------------------------------------------------------------------------


def test_email_address_is_trimmed_and_still_a_string() -> None:
    email = EmailAddress("  Ada@Example.com ")
    assert email == "Ada@Example.com"  # case kept: lookups are exact-match
    assert isinstance(email, str)


@pytest.mark.parametrize("value", ["", "ada", "ada@example", "a da@example.com", "x" * 315 + "@a.com"])
def test_invalid_email_addresses_are_rejected(value: str) -> None:
    with pytest.raises(InvalidEmailAddress):
        EmailAddress(value)


@pytest.mark.parametrize("value", ["ab", "x" * 51, "ada lovelace", "ada@home"])
def test_invalid_usernames_are_rejected(value: str) -> None:
    with pytest.raises(InvalidUsername):
        Username(value)


def test_username_allows_handle_characters() -> None:
    assert Username(" ada.lovelace_1-x ") == "ada.lovelace_1-x"


# --- Entity uses the value objects ----------------------------------------------------------------


def test_entity_turns_plain_strings_into_value_objects() -> None:
    account = _account(email=" ada@example.com ", username="ADA42")
    assert isinstance(account.email, EmailAddress)
    assert isinstance(account.username, Username)
    assert account.email == "ada@example.com"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [("email", "not-an-email", InvalidEmailAddress), ("username", "a b", InvalidUsername)],
)
def test_entity_cannot_hold_invalid_values(field: str, value: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        _account(**{field: value})


# --- Business questions ---------------------------------------------------------------------------


def test_account_is_locked_only_until_expiry() -> None:
    assert _account(locked_until=NOW + timedelta(minutes=5)).is_locked(NOW)
    assert not _account(locked_until=NOW - timedelta(seconds=1)).is_locked(NOW)
    assert not _account().is_locked(NOW)


def test_lock_check_requires_timezone_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _account().is_locked(datetime.now())


# --- Behaviours -----------------------------------------------------------------------------------


def test_verify_email_keeps_first_timestamp() -> None:
    account = _account()
    assert account.verify_email(at=NOW)
    assert not account.verify_email(at=NOW + timedelta(days=1))
    assert account.email_verified_at == NOW
    assert account.is_email_verified


def test_clear_failed_logins_reports_whether_anything_changed() -> None:
    assert not _account().clear_failed_logins()
    account = _account(failed_login_attempts=3, locked_until=NOW)
    assert account.clear_failed_logins()
    assert (account.failed_login_attempts, account.locked_until) == (0, None)


def test_change_password_requires_a_hash() -> None:
    account = _account()
    account.change_password("new-hash")
    assert account.password_hash == "new-hash"
    with pytest.raises(InvalidPasswordHash):
        account.change_password("")


def test_mfa_lifecycle() -> None:
    account = _account()
    with pytest.raises(MfaNotStarted):
        account.enable_mfa(at=NOW)
    account.start_mfa_setup("encrypted-secret")
    assert not account.is_mfa_enabled
    account.enable_mfa(at=NOW)
    assert account.is_mfa_enabled
    with pytest.raises(MfaAlreadyEnabled):
        account.start_mfa_setup("another-secret")
    account.disable_mfa()
    assert (account.mfa_secret_encrypted, account.mfa_enabled_at) == (None, None)


def test_apply_refreshes_every_field() -> None:
    account, stored = _account(), _account(email_verified_at=NOW, token_version=4)
    account.apply(stored)
    assert account == stored


# --- Policy ---------------------------------------------------------------------------------------


def test_lockout_expiry_adds_the_lockout_window() -> None:
    assert lockout_expiry(now=NOW, lockout_minutes=15) == NOW + timedelta(minutes=15)
    with pytest.raises(ValueError, match="timezone-aware"):
        lockout_expiry(now=datetime(2026, 1, 1), lockout_minutes=15)
