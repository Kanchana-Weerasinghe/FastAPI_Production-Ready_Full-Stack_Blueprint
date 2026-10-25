"""UserAccount domain rules: value objects, invariants, behaviours and guards. No database, no framework."""

from datetime import datetime, timedelta

import pytest

from app.modules.users.domain.exceptions import (
    InvalidEmailAddress,
    InvalidPasswordHash,
    InvalidRole,
    InvalidUsername,
    MfaAlreadyEnabled,
    MfaNotStarted,
)
from app.modules.users.domain.value_objects import EmailAddress, PasswordHash, Role, Username
from tests.business_rules.users_builders import HASH, NOW, OTHER_HASH, an_account

# --- BR-01 · email -------------------------------------------------------------------------------


@pytest.mark.br("BR-01", "TC-01-1")
def test_br_01_valid_email_is_accepted_and_trimmed() -> None:
    assert EmailAddress("  ada@example.com ") == "ada@example.com"


@pytest.mark.br("BR-01", "TC-01-2")
@pytest.mark.parametrize("value", ["", "ada", "ada@example", "a da@example.com", "x" * 315 + "@a.com"])
def test_br_01_malformed_email_is_rejected(value: str) -> None:
    with pytest.raises(InvalidEmailAddress) as error:
        EmailAddress(value)
    assert error.value.code == "invalid_email"


@pytest.mark.br("BR-01", "TC-01-3")
def test_br_01_account_can_never_hold_an_invalid_email() -> None:
    with pytest.raises(InvalidEmailAddress):
        an_account(email="not-an-email")


# --- BR-02 · username ----------------------------------------------------------------------------


@pytest.mark.br("BR-02", "TC-02-1")
def test_br_02_valid_username_is_accepted_and_trimmed() -> None:
    assert Username(" ada.lovelace_1-x ") == "ada.lovelace_1-x"


@pytest.mark.br("BR-02", "TC-02-2")
@pytest.mark.parametrize("value", ["ab", "x" * 51, "ada lovelace", "ada@home"])
def test_br_02_invalid_username_is_rejected(value: str) -> None:
    with pytest.raises(InvalidUsername) as error:
        Username(value)
    assert error.value.code == "invalid_username"


# --- BR-03 · password hash -----------------------------------------------------------------------


@pytest.mark.br("BR-03", "TC-03-1")
def test_br_03_bcrypt_hash_is_accepted() -> None:
    assert PasswordHash(HASH) == HASH


@pytest.mark.br("BR-03", "TC-03-2")
@pytest.mark.parametrize("value", ["", "MySecret123!", "$2b$12$tooshort", "hash"])
def test_br_03_plain_password_is_never_accepted_as_hash(value: str) -> None:
    with pytest.raises(InvalidPasswordHash):
        PasswordHash(value)


@pytest.mark.br("BR-03", "TC-03-3")
def test_br_03_change_password_rejects_plain_password_and_keeps_old_hash() -> None:
    account = an_account()
    with pytest.raises(InvalidPasswordHash):
        account.change_password("MyNewPassword1!")
    assert account.password_hash == HASH
    account.change_password(OTHER_HASH)
    assert account.password_hash == OTHER_HASH


# --- BR-04 · role --------------------------------------------------------------------------------


@pytest.mark.br("BR-04", "TC-04-1")
def test_br_04_known_roles_are_parsed() -> None:
    assert Role.parse("user") is Role.USER
    assert Role.parse("admin") is Role.ADMIN


@pytest.mark.br("BR-04", "TC-04-2")
def test_br_04_unknown_role_is_rejected() -> None:
    with pytest.raises(InvalidRole) as error:
        Role.parse("superadmin")
    assert error.value.code == "invalid_role"
    with pytest.raises(InvalidRole):
        an_account(role="superadmin")


# --- BR-06 · verify email once -------------------------------------------------------------------


@pytest.mark.br("BR-06", "TC-06-1")
def test_br_06_verifying_twice_keeps_the_first_date() -> None:
    account = an_account()
    assert account.verify_email(at=NOW) is True
    assert account.verify_email(at=NOW + timedelta(days=1)) is False
    assert account.email_verified_at == NOW


# --- BR-07 · MFA lifecycle -----------------------------------------------------------------------


@pytest.mark.br("BR-07", "TC-07-1")
def test_br_07_mfa_cannot_be_enabled_before_setup() -> None:
    with pytest.raises(MfaNotStarted) as error:
        an_account().enable_mfa(at=NOW)
    assert error.value.code == "mfa_not_started"


@pytest.mark.br("BR-07", "TC-07-2")
def test_br_07_setup_then_enable_turns_mfa_on() -> None:
    account = an_account()
    account.start_mfa_setup("encrypted-secret")
    assert account.mfa_enabled_at is None
    account.enable_mfa(at=NOW)
    assert account.mfa_enabled_at == NOW


@pytest.mark.br("BR-07", "TC-07-3")
def test_br_07_setup_is_refused_while_mfa_is_enabled() -> None:
    account = an_account(mfa_secret_encrypted="encrypted-secret", mfa_enabled_at=NOW)
    with pytest.raises(MfaAlreadyEnabled):
        account.start_mfa_setup("another-secret")
    assert account.mfa_secret_encrypted == "encrypted-secret"


@pytest.mark.br("BR-07", "TC-07-4")
def test_br_07_disable_clears_secret_and_activation() -> None:
    account = an_account(mfa_secret_encrypted="encrypted-secret", mfa_enabled_at=NOW)
    account.disable_mfa()
    assert (account.mfa_secret_encrypted, account.mfa_enabled_at) == (None, None)


# --- BR-09 · locked accounts ---------------------------------------------------------------------


@pytest.mark.br("BR-09", "TC-09-1")
def test_br_09_account_is_locked_only_while_expiry_is_in_the_future() -> None:
    assert an_account(locked_until=NOW + timedelta(minutes=5)).is_locked(NOW) is True
    assert an_account(locked_until=NOW - timedelta(seconds=1)).is_locked(NOW) is False
    assert an_account(locked_until=None).is_locked(NOW) is False


@pytest.mark.br("BR-09", "TC-09-2")
def test_br_09_lock_check_requires_timezone_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        an_account().is_locked(datetime(2026, 1, 1))
