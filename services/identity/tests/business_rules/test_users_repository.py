"""SqlAlchemyUserRepository against the real database: mapping, invalid stored data, constraints, atomic counters."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.modules.users.domain.exceptions import InvalidPasswordHash, InvalidRole
from app.modules.users.domain.value_objects import EmailAddress, PasswordHash, Role, Username
from app.modules.users.infrastructure.persistence.models import Users
from app.modules.users.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from tests.business_rules.users_builders import HASH


async def _stored_user(session: AsyncSession, **overrides: object) -> Users:
    row = Users(
        id=uuid.uuid4(),
        email=overrides.pop("email", f"repo_{uuid.uuid4().hex[:8]}@example.com"),
        username=overrides.pop("username", f"R{uuid.uuid4().hex[:8].upper()}"),
        _password=overrides.pop("password", HASH),
        created_by="test",
        updated_by="test",
        **overrides,
    )
    session.add(row)
    await session.flush()
    return row


@pytest.mark.br("BR-01", "TC-01-6")
async def test_br_01_account_round_trips_with_value_objects(db_session: AsyncSession) -> None:
    locked_until = datetime.now(UTC) + timedelta(minutes=5)
    row = await _stored_user(db_session, role="admin", failed_login_attempts=2, locked_until=locked_until)

    account = await SqlAlchemyUserRepository(db_session).get_account_by_id(row.id)

    assert account.id == row.id
    assert isinstance(account.email, EmailAddress)
    assert account.email == row.email
    assert isinstance(account.username, Username)
    assert isinstance(account.password_hash, PasswordHash)
    assert account.role is Role.ADMIN
    assert (account.failed_login_attempts, account.locked_until) == (2, locked_until)


@pytest.mark.br("BR-03", "TC-03-6")
async def test_br_03_stored_plain_password_never_reaches_the_use_cases(db_session: AsyncSession) -> None:
    row = await _stored_user(db_session, password="plain-text-password")
    with pytest.raises(InvalidPasswordHash):
        await SqlAlchemyUserRepository(db_session).get_account_by_id(row.id)


@pytest.mark.br("BR-03", "TC-03-7")
async def test_br_03_token_version_is_counted_in_the_database(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)
    row = await _stored_user(db_session)
    stale = await repository.get_account_by_id(row.id)  # token_version 0, never reloaded

    assert await repository.increment_token_version(stale.id) == 1
    assert await repository.increment_token_version(stale.id) == 2


@pytest.mark.br("BR-04", "TC-04-3")
async def test_br_04_stored_unknown_role_never_reaches_the_use_cases(db_session: AsyncSession) -> None:
    row = await _stored_user(db_session, role="superadmin")
    with pytest.raises(InvalidRole):
        await SqlAlchemyUserRepository(db_session).get_account_by_id(row.id)


@pytest.mark.br("BR-05", "TC-05-2")
async def test_br_05_unique_constraint_rejects_a_racing_duplicate(db_session: AsyncSession) -> None:
    existing = await _stored_user(db_session)
    repository = SqlAlchemyUserRepository(db_session)

    with pytest.raises(ConflictError):
        async with db_session.begin_nested():  # contain the failed insert, like the request transaction would
            await repository.create_account(
                {
                    "email": existing.email,
                    "username": "RACER01",
                    "password": HASH,
                    "created_by": "test",
                    "updated_by": "test",
                }
            )

    count = await db_session.scalar(select(func.count()).select_from(Users).where(Users.email == existing.email))
    assert count == 1


@pytest.mark.br("BR-08", "TC-08-7")
async def test_br_08_failed_sign_ins_are_counted_in_the_database(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)
    row = await _stored_user(db_session)
    stale = await repository.get_account_by_id(row.id)  # failed_login_attempts 0, never reloaded
    lock_until = datetime.now(UTC) + timedelta(minutes=15)

    for _ in range(3):
        await repository.register_failed_login(stale.id, max_attempts=5, lock_until=lock_until)

    attempts = await db_session.scalar(select(Users.failed_login_attempts).where(Users.id == row.id))
    assert attempts == 3
