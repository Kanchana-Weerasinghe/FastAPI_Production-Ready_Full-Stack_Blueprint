"""UserAccount rules through the real HTTP API and database (each test runs in a rolled-back transaction)."""

from typing import Any

import pytest
from sqlalchemy import select, update

from app.core.config import config
from app.main import db
from app.modules.users.infrastructure.persistence.models import Users
from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}
SECOND_USER = {"email": "second_user@email.com", "password": "SecurePass123!"}
PUBLIC_PROFILE_FIELDS = {"id", "email", "username", "role", "emailVerified", "mfaEnabled"}


async def _wrong_password_sign_ins(api_client: Any, email: str, times: int) -> None:
    for _ in range(times):
        response = await api_client.post("/v1/auth/signin", json={"email": email, "password": "wrong-password"})
        assert response.json()["code"] == "invalid_credentials"


@pytest.mark.br("BR-01", "TC-01-5")
async def test_br_01_sign_up_with_invalid_email_is_rejected(client: Any) -> None:
    response = await (await client()).post(
        "/v1/auth/signup", json={"email": "not-an-email", "password": "SecurePass123!"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


@pytest.mark.br("BR-05", "TC-05-1")
async def test_br_05_duplicate_email_does_not_create_a_second_account(client: Any, mock_autosend: Any) -> None:
    mock_autosend.send_email.reset_mock()
    api_client = await client()
    response = await api_client.post("/v1/auth/signup", json={**FIRST_USER, "password": "AnotherPass123!"})
    assert response.status_code == 201  # same answer as a new sign-up: no account enumeration
    mock_autosend.send_email.assert_not_called()
    assert (await api_client.post("/v1/auth/signin", json=FIRST_USER)).status_code == 200
    replaced = await api_client.post("/v1/auth/signin", json={**FIRST_USER, "password": "AnotherPass123!"})
    assert replaced.status_code == 401


@pytest.mark.br("BR-08", "TC-08-6")
async def test_br_08_five_wrong_passwords_lock_the_account(client: Any) -> None:
    await _wrong_password_sign_ins(await client(), SECOND_USER["email"], config.LOGIN_MAX_FAILED_ATTEMPTS)
    async with db.session_scope() as session:
        locked_until = await session.scalar(select(Users.locked_until).where(Users.email == SECOND_USER["email"]))
    assert locked_until is not None


@pytest.mark.br("BR-09", "TC-09-3")
async def test_br_09_locked_account_cannot_sign_in_even_with_correct_password(client: Any) -> None:
    api_client = await client()
    await _wrong_password_sign_ins(api_client, SECOND_USER["email"], config.LOGIN_MAX_FAILED_ATTEMPTS)
    response = await api_client.post("/v1/auth/signin", json=SECOND_USER)
    assert response.status_code == 401
    assert response.json()["code"] == "account_locked"


@pytest.mark.br("BR-10", "TC-10-2")
async def test_br_10_user_deletes_own_account_and_is_signed_out(client: Any) -> None:
    credentials = {"email": "br10_delete_me@example.com", "password": "SecurePass123!"}
    await (await client()).post("/v1/auth/signup", json=credentials)
    api_client = await client(**credentials)

    response = await api_client.delete("/v2/user/me")

    assert response.status_code == 204
    expired = [c for c in response.headers.get_list("set-cookie") if c.startswith(f"{config.AUTH_COOKIE_NAME}=")]
    assert expired, "the access-token cookie must be expired"
    assert "Max-Age=0" in expired[0]
    assert (await api_client.get("/v2/user/me")).status_code == 401


@pytest.mark.br("BR-11", "TC-11-1")
async def test_br_11_user_sees_own_profile_without_secrets(client: Any) -> None:
    response = await (await client(**FIRST_USER)).get("/v2/user/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == FIRST_USER["email"]
    assert set(body) == PUBLIC_PROFILE_FIELDS  # no password hash, MFA secret or lock data


@pytest.mark.br("BR-11", "TC-11-2")
async def test_br_11_profile_requires_a_session(client: Any) -> None:
    assert (await (await client()).get("/v2/user/me")).status_code == 401


@pytest.mark.br("BR-11", "TC-11-3")
async def test_br_11_normal_user_cannot_list_users(client: Any) -> None:
    response = await (await client(**FIRST_USER)).get("/v2/users/")
    assert response.status_code == 403


@pytest.mark.br("BR-11", "TC-11-4")
async def test_br_11_admin_can_list_users(client: Any) -> None:
    async with db.session_scope() as session:
        await session.execute(update(Users).where(Users.email == FIRST_USER["email"]).values(role="admin"))
    response = await (await client(**FIRST_USER)).get("/v2/users/")
    assert response.status_code == 200
    assert response.json()["founds"]
