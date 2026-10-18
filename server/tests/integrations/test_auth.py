from typing import Any

import pytest

from app.core.config import config

NEW_USER_CREDENTIALS = {"email": "new_user@email.com", "password": "SecurePass123!"}
FIRST_USER_CREDENTIALS = {"email": "first_user@email.com", "password": "SecurePass123!"}


async def test_signup_success(client: Any, mock_autosend: Any) -> None:
    """Integration test verifying a successful user registration and that a welcome email is sent via Autosend."""
    mock_autosend.send_email.reset_mock()
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signup",
        json=NEW_USER_CREDENTIALS,
    )
    assert response.status_code == 201
    recipients_and_subjects = [(c.args[0], c.args[1]) for c in mock_autosend.send_email.call_args_list]
    assert (NEW_USER_CREDENTIALS["email"], "Welcome to FastAPI Template!") in recipients_and_subjects
    assert any(subject.startswith("Confirm your email") for _, subject in recipients_and_subjects)
    signin_response = await api_client.post(
        "/v1/auth/signin",
        json=NEW_USER_CREDENTIALS,
    )
    assert signin_response.status_code == 200


async def test_signup_duplicate_email(client: Any, mock_autosend: Any) -> None:
    """Integration test verifying that trying to register an existing email is rejected or handled gracefully without emailing."""
    mock_autosend.send_email.reset_mock()
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signup",
        json={**FIRST_USER_CREDENTIALS, "password": "NewSecurePass123!"},
    )
    assert response.status_code == 201
    mock_autosend.send_email.assert_not_called()
    signin_response = await api_client.post(
        "/v1/auth/signin",
        json=FIRST_USER_CREDENTIALS,
    )
    assert signin_response.status_code == 200
    signin_new_response = await api_client.post(
        "/v1/auth/signin",
        json={**FIRST_USER_CREDENTIALS, "password": "NewSecurePass123!"},
    )
    assert signin_new_response.status_code == 401


async def test_signup_invalid_email(client: Any) -> None:
    """Integration test verifying that signing up with an invalid email address format raises a 422 Validation Error."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signup",
        json={**FIRST_USER_CREDENTIALS, "email": "not_an_email"},
    )
    assert response.status_code == 422


async def test_signup_missing_fields(client: Any) -> None:
    """Integration test verifying that registering with missing mandatory fields (like password) raises a 422 Validation Error."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signup",
        json={"email": "new_user@email.com"},
    )
    assert response.status_code == 422


async def test_signin_success(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test verifying that a user can sign in with valid credentials and receive an authentication cookie."""
    monkeypatch.setattr(config, "APP_DOMAIN", "localhost")
    monkeypatch.setattr(config, "ENVIRONMENT", "development")

    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin",
        json=FIRST_USER_CREDENTIALS,
    )
    assert response.status_code == 200
    assert "set-cookie" in response.headers
    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header is not None, "The response failed to return a Set-Cookie header."
    assert f"{config.AUTH_COOKIE_NAME}=" in set_cookie_header
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header.lower()
    assert "SameSite=Lax" in set_cookie_header or "samesite=lax" in set_cookie_header.lower()
    assert "domain=localhost" in set_cookie_header.lower()
    assert "path=/" in set_cookie_header.lower()
    assert config.AUTH_COOKIE_NAME in api_client.cookies
    assert api_client.cookies[config.AUTH_COOKIE_NAME] is not None


async def test_signin_incorrect_password(client: Any) -> None:
    """Integration test verifying that logging in with a wrong password returns a 401 Unauthorized status code."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin",
        json={"email": "first_user@email.com", "password": "wrong_password"},
    )
    assert response.status_code == 401


async def test_signin_non_existent_user(client: Any) -> None:
    """Integration test verifying that logging in with an email that is not registered returns a 401 Unauthorized status code."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin",
        json={"email": "does_not_exist@email.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 401


async def test_signin_invalid_email(client: Any) -> None:
    """Integration test verifying that logging in with an invalid email address format raises a 422 Validation Error."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin",
        json={**FIRST_USER_CREDENTIALS, "email": "not_an_email"},
    )
    assert response.status_code == 422


async def test_signin_missing_fields(client: Any) -> None:
    """Integration test verifying that logging in with missing mandatory fields raises a 422 Validation Error."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin",
        json={"email": "first_user@email.com"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "password",
    ["short1!", "x" * 73, "é" * 37],
    ids=["below-minimum-length", "above-72-bytes", "multibyte-above-72-bytes"],
)
async def test_signup_rejects_invalid_password(client: Any, password: str) -> None:
    """Integration test verifying that sign-up rejects passwords shorter than 8 characters or longer than bcrypt's 72-byte limit."""
    api_client = await client()
    response = await api_client.post("/v1/auth/signup", json={"email": "weak@email.com", "password": password})
    assert response.status_code == 422


async def test_signin_rejects_overlong_password(client: Any) -> None:
    """Integration test verifying that sign-in returns 422 (not a 500 from bcrypt) for passwords above 72 bytes."""
    api_client = await client()
    response = await api_client.post(
        "/v1/auth/signin", json={"email": FIRST_USER_CREDENTIALS["email"], "password": "x" * 73}
    )
    assert response.status_code == 422


async def test_signout_clears_session(client: Any) -> None:
    """Integration test verifying that sign-out expires the auth cookie so subsequent requests are unauthenticated."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    assert (await api_client.get("/v2/user/me")).status_code == 200
    response = await api_client.post("/v1/auth/signout")
    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert config.AUTH_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie
    assert (await api_client.get("/v2/user/me")).status_code == 401


async def test_signout_without_session(client: Any) -> None:
    """Integration test verifying that sign-out is idempotent and succeeds without an active session."""
    api_client = await client()
    response = await api_client.post("/v1/auth/signout")
    assert response.status_code == 204
