"""
UserAccount integration cases (developer-owned): the real HTTP API plus database state that a black-box
client cannot see or set up (expired locks, deactivated accounts, audit rows, captured emails).
Each test runs in a rolled-back transaction. Black-box acceptance cases live in qa/identity-acceptance.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select, update

from app.core.config import config
from app.main import db
from app.modules.audit.infrastructure.persistence.models import AuditLogs
from app.modules.todos.infrastructure.persistence.models import Todos
from app.modules.users.infrastructure.persistence.models import Users
from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}
SECOND_USER = {"email": "second_user@email.com", "password": "SecurePass123!"}
PUBLIC_PROFILE_FIELDS = {"id", "email", "username", "role", "emailVerified", "mfaEnabled"}


async def _set_user(email: str, **values: Any) -> None:
    async with db.session_scope() as session:
        await session.execute(update(Users).where(Users.email == email).values(**values))


async def _scalar(statement: Any) -> Any:
    async with db.session_scope() as session:
        return await session.scalar(statement)


def _token_from_last_email(mock_autosend: Any) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-%]+)", mock_autosend.send_email.call_args.args[2])
    assert match, "the verification email must contain a token link"
    return match.group(1)


async def _wrong_password_sign_ins(api_client: Any, email: str, times: int) -> None:
    for _ in range(times):
        response = await api_client.post("/v1/auth/signin", json={"email": email, "password": "wrong-password"})
        assert response.json()["code"] == "invalid_credentials"


@pytest.mark.br("BR-08", "TC-08-6")
async def test_br_08_five_wrong_passwords_lock_the_account(client: Any) -> None:
    await _wrong_password_sign_ins(await client(), SECOND_USER["email"], config.LOGIN_MAX_FAILED_ATTEMPTS)
    async with db.session_scope() as session:
        locked_until = await session.scalar(select(Users.locked_until).where(Users.email == SECOND_USER["email"]))
    assert locked_until is not None


@pytest.mark.br("BR-06", "TC-06-3")
async def test_br_06_verification_link_verifies_once(client: Any, mock_autosend: Any) -> None:
    credentials = {"email": f"br06_{uuid.uuid4().hex[:6]}@example.com", "password": "SecurePass123!"}
    anonymous = await client()
    await anonymous.post("/v1/auth/signup", json=credentials)
    token = _token_from_last_email(mock_autosend)

    assert (await anonymous.post("/v1/auth/verify-email", json={"token": token})).status_code == 204
    assert (await (await client(**credentials)).get("/v2/user/me")).json()["emailVerified"] is True
    reused = await (await client()).post("/v1/auth/verify-email", json={"token": token})
    assert reused.status_code == 400
    assert reused.json()["code"] == "invalid_or_expired_token"


@pytest.mark.br("BR-09", "TC-09-4")
async def test_br_09_expired_lock_allows_sign_in_and_is_cleared(client: Any) -> None:
    await _set_user(
        SECOND_USER["email"], failed_login_attempts=2, locked_until=datetime.now(UTC) - timedelta(minutes=1)
    )
    response = await (await client()).post("/v1/auth/signin", json=SECOND_USER)
    assert response.status_code == 200
    stored = await _scalar(
        select(func.row(Users.failed_login_attempts, Users.locked_until)).where(Users.email == SECOND_USER["email"])
    )
    assert tuple(stored) == (0, None)


@pytest.mark.br("BR-10", "TC-10-3")
async def test_br_10_deletion_audits_and_removes_owned_data(client: Any) -> None:
    credentials = {"email": f"br10_{uuid.uuid4().hex[:6]}@example.com", "password": "SecurePass123!"}
    await (await client()).post("/v1/auth/signup", json=credentials)
    api_client = await client(**credentials)
    user_id = uuid.UUID((await api_client.get("/v2/user/me")).json()["id"])
    assert (await api_client.post("/v2/todos/", json={"title": "Owned by the deleted user"})).status_code == 201
    owned_file = Path(config.UPLOAD_DIR) / str(user_id) / "notes.txt"
    owned_file.parent.mkdir(parents=True, exist_ok=True)
    owned_file.write_text("private", encoding="utf-8")

    assert (await api_client.delete("/v2/user/me")).status_code == 204

    audits = await _scalar(
        select(func.count())
        .select_from(AuditLogs)
        .where(AuditLogs.action == "user.deleted", AuditLogs.resource_id == str(user_id))
    )
    todos = await _scalar(select(func.count()).select_from(Todos).where(Todos.user_id == user_id))
    assert audits == 1
    assert todos == 0
    assert not owned_file.exists()  # removed by the after-commit cleanup


@pytest.mark.br("BR-12", "TC-12-1")
async def test_br_12_inactive_account_cannot_sign_in(client: Any) -> None:
    await _set_user(SECOND_USER["email"], is_active=False)
    api_client = await client()
    inactive = await api_client.post("/v1/auth/signin", json=SECOND_USER)
    assert inactive.status_code == 401
    assert inactive.json()["code"] == "account_inactive"
    wrong = await api_client.post("/v1/auth/signin", json={**SECOND_USER, "password": "wrong-password"})
    assert wrong.json()["code"] == "invalid_credentials"  # no hint about the account state without the password


@pytest.mark.br("BR-12", "TC-12-2")
async def test_br_12_existing_session_stops_working_after_deactivation(client: Any) -> None:
    api_client = await client(**SECOND_USER)
    assert (await api_client.get("/v2/user/me")).status_code == 200
    await _set_user(SECOND_USER["email"], is_active=False)
    assert (await api_client.get("/v2/user/me")).status_code == 401
