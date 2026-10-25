"""UserUseCases workflows with in-memory fakes: the application layer coordinates domain rules and ports."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import config
from app.core.errors import BadRequestError
from tests.business_rules.users_builders import HASH, OTHER_HASH, UseCaseWorld

# --- BR-01 / BR-02 · registration validates values -----------------------------------------------


@pytest.mark.br("BR-01", "TC-01-4")
async def test_br_01_create_user_rejects_invalid_email_and_stores_nothing(world: UseCaseWorld) -> None:
    with pytest.raises(BadRequestError) as error:
        await world.use_cases.create_user(email="not-an-email", password_hash=HASH, username="ADA42")
    assert error.value.code == "invalid_email"
    assert world.repository.users_db == []


@pytest.mark.br("BR-02", "TC-02-3")
async def test_br_02_create_user_rejects_invalid_username_and_stores_nothing(world: UseCaseWorld) -> None:
    with pytest.raises(BadRequestError) as error:
        await world.use_cases.create_user(email="ada@example.com", password_hash=HASH, username="a b")
    assert error.value.code == "invalid_username"
    assert world.repository.users_db == []


# --- BR-03 · credentials -------------------------------------------------------------------------


@pytest.mark.br("BR-03", "TC-03-4")
async def test_br_03_set_password_rejects_plain_password_without_side_effects(world: UseCaseWorld) -> None:
    row = world.repository.add_row()
    user = await world.use_cases.get_by_id(row.id)
    with pytest.raises(BadRequestError) as error:
        await world.use_cases.set_password(user, "MyNewPassword1!")
    assert error.value.code == "invalid_password_hash"
    assert world.repository.updates == []
    assert (await world.use_cases.get_by_id(row.id)).token_version == 0


@pytest.mark.br("BR-03", "TC-03-5")
async def test_br_03_set_password_saves_hash_and_revokes_sessions(world: UseCaseWorld) -> None:
    row = world.repository.add_row()
    user = await world.use_cases.get_by_id(row.id)
    await world.use_cases.set_password(user, OTHER_HASH)
    stored = await world.use_cases.get_by_id(row.id)
    assert stored.password_hash == OTHER_HASH
    assert stored.token_version == 1


# --- BR-06 · email verification ------------------------------------------------------------------


@pytest.mark.br("BR-06", "TC-06-2")
async def test_br_06_email_verification_is_saved_only_once(world: UseCaseWorld) -> None:
    row = world.repository.add_row()
    user = await world.use_cases.get_by_id(row.id)
    await world.use_cases.mark_email_verified(user)
    first_date = user.email_verified_at
    await world.use_cases.mark_email_verified(user)
    assert first_date is not None
    assert user.email_verified_at == first_date
    assert [list(update) for update in world.repository.updates] == [["email_verified_at"]]


# --- BR-07 · MFA ---------------------------------------------------------------------------------


@pytest.mark.br("BR-07", "TC-07-5")
async def test_br_07_enabling_mfa_before_setup_is_a_bad_request(world: UseCaseWorld) -> None:
    row = world.repository.add_row()
    user = await world.use_cases.get_by_id(row.id)
    with pytest.raises(BadRequestError) as error:
        await world.use_cases.set_mfa_secret(user, "encrypted-secret", enabled=True)
    assert error.value.code == "mfa_not_started"
    assert world.repository.updates == []


# --- BR-08 · lockout -----------------------------------------------------------------------------


@pytest.mark.br("BR-08", "TC-08-3")
async def test_br_08_failure_below_the_limit_is_counted_without_locking(world: UseCaseWorld) -> None:
    row = world.repository.add_row(failed_login_attempts=config.LOGIN_MAX_FAILED_ATTEMPTS - 2)
    await world.use_cases.record_failed_login(await world.use_cases.get_by_id(row.id))
    stored = await world.use_cases.get_by_id(row.id)
    assert stored.failed_login_attempts == config.LOGIN_MAX_FAILED_ATTEMPTS - 1
    assert stored.locked_until is None
    assert world.uow.persisted_on_failure is True  # kept although sign-in answers 401


@pytest.mark.br("BR-08", "TC-08-4")
async def test_br_08_reaching_the_limit_locks_for_the_configured_duration(world: UseCaseWorld) -> None:
    row = world.repository.add_row(failed_login_attempts=config.LOGIN_MAX_FAILED_ATTEMPTS - 1)
    before = datetime.now(UTC)
    await world.use_cases.record_failed_login(await world.use_cases.get_by_id(row.id))
    stored = await world.use_cases.get_by_id(row.id)
    expected = before + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
    assert stored.locked_until is not None
    assert abs((stored.locked_until - expected).total_seconds()) < 5
    assert stored.failed_login_attempts == 0  # the counter restarts after locking


@pytest.mark.br("BR-08", "TC-08-5")
async def test_br_08_successful_sign_in_clears_failures_and_saves_only_when_needed(world: UseCaseWorld) -> None:
    locked = world.repository.add_row(failed_login_attempts=3, locked_until=datetime.now(UTC))
    await world.use_cases.reset_failed_logins(await world.use_cases.get_by_id(locked.id))
    stored = await world.use_cases.get_by_id(locked.id)
    assert (stored.failed_login_attempts, stored.locked_until) == (0, None)
    assert len(world.repository.updates) == 1

    clean = world.repository.add_row()
    await world.use_cases.reset_failed_logins(await world.use_cases.get_by_id(clean.id))
    assert len(world.repository.updates) == 1  # nothing to reset, nothing saved


# --- BR-10 · account deletion --------------------------------------------------------------------


@pytest.mark.br("BR-10", "TC-10-1")
async def test_br_10_files_are_removed_only_after_the_deletion_commits(world: UseCaseWorld) -> None:
    row = world.repository.add_row()
    user = await world.use_cases.get_by_id(row.id)

    await world.use_cases.delete_account(user)

    assert world.repository.deleted == [row.id]
    world.audit.record.assert_awaited_once()
    audit_call = world.audit.record.await_args
    assert audit_call is not None
    assert audit_call.args[0] == "user.deleted"
    assert world.storage.deleted_owners == []  # not before the commit
    await world.uow.commit()
    assert world.storage.deleted_owners == [row.id]  # only after it
