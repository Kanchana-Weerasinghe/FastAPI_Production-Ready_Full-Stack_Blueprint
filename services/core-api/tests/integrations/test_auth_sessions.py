import re
from typing import Any

import pyotp
import pytest

from app.core.config import config

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}
SECOND_USER = {"email": "second_user@email.com", "password": "SecurePass123!"}


def _replace_cookie(api_client: Any, name: str, value: str) -> None:
    """Swaps a cookie's value in the jar, keeping the domain/path the server set it with."""
    existing = next(c for c in api_client.cookies.jar if c.name == name)
    domain, path = existing.domain, existing.path
    api_client.cookies.delete(name)
    api_client.cookies.set(name, value, domain=domain, path=path)


def _token_from_last_email(mock_autosend: Any) -> str:
    html = mock_autosend.send_email.call_args.args[2]
    match = re.search(r"token=([A-Za-z0-9_\-%]+)", html)
    assert match, html
    return match.group(1)


async def test_signin_sets_session_cookies(client: Any) -> None:
    """Integration test verifying sign-in sets HttpOnly access/refresh cookies and a readable CSRF cookie."""
    api_client = await client()
    response = await api_client.post("/v1/auth/signin", json=FIRST_USER)
    assert response.status_code == 200
    assert response.json() == {"mfaRequired": False, "mfaToken": None}
    cookies = response.headers.get_list("set-cookie")
    by_name = {c.split("=", 1)[0]: c for c in cookies}
    assert "HttpOnly" in by_name[config.AUTH_COOKIE_NAME]
    assert "HttpOnly" in by_name[config.REFRESH_COOKIE_NAME]
    assert f"Path={config.REFRESH_COOKIE_PATH}" in by_name[config.REFRESH_COOKIE_NAME]
    assert "HttpOnly" not in by_name[config.CSRF_COOKIE_NAME]


async def test_unsafe_request_without_csrf_header_is_rejected(client: Any) -> None:
    """Integration test verifying cookie-authenticated unsafe requests need the X-CSRF-Token header."""
    api_client = await client(**FIRST_USER)
    csrf = api_client.headers.pop(config.CSRF_HEADER_NAME)
    response = await api_client.post("/v2/todos/", json={"title": "csrf"})
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    api_client.headers[config.CSRF_HEADER_NAME] = csrf
    assert (await api_client.post("/v2/todos/", json={"title": "csrf"})).status_code == 201


async def test_refresh_rotates_and_detects_reuse(client: Any) -> None:
    """Integration test verifying refresh rotates the token and replaying an old token revokes the family."""
    api_client = await client(**FIRST_USER)
    old_refresh = api_client.cookies.get(config.REFRESH_COOKIE_NAME)

    response = await api_client.post("/v1/auth/refresh")
    assert response.status_code == 204
    new_refresh = api_client.cookies.get(config.REFRESH_COOKIE_NAME)
    assert new_refresh
    assert new_refresh != old_refresh
    api_client.headers[config.CSRF_HEADER_NAME] = api_client.cookies.get(config.CSRF_COOKIE_NAME)

    _replace_cookie(api_client, config.REFRESH_COOKIE_NAME, old_refresh)
    replay = await api_client.post("/v1/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["code"] == "refresh_token_reused"

    _replace_cookie(api_client, config.REFRESH_COOKIE_NAME, new_refresh)
    assert (await api_client.post("/v1/auth/refresh")).status_code == 401


async def test_signout_everywhere_revokes_access_tokens(client: Any) -> None:
    """Integration test verifying sign-out-everywhere invalidates already-issued access tokens immediately."""
    api_client = await client(**FIRST_USER)
    access = api_client.cookies.get(config.AUTH_COOKIE_NAME)
    assert (await api_client.post("/v1/auth/signout-all")).status_code == 204
    api_client.cookies.set(config.AUTH_COOKIE_NAME, access)
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"


async def test_account_locks_after_repeated_failures(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test verifying the account locks after LOGIN_MAX_FAILED_ATTEMPTS wrong passwords."""
    monkeypatch.setattr(config, "LOGIN_MAX_FAILED_ATTEMPTS", 3)
    api_client = await client()
    for _ in range(3):
        bad = await api_client.post("/v1/auth/signin", json={**SECOND_USER, "password": "wrong-password"})
        assert bad.json()["code"] == "invalid_credentials"
    locked = await api_client.post("/v1/auth/signin", json=SECOND_USER)
    assert locked.status_code == 401
    assert locked.json()["code"] == "account_locked"


async def test_password_reset_flow(client: Any, mock_autosend: Any) -> None:
    """Integration test verifying forgot/reset: single-use link, new password works, old sessions are revoked."""
    session = await client(**FIRST_USER)
    old_access = session.cookies.get(config.AUTH_COOKIE_NAME)

    anonymous = await client()
    assert (await anonymous.post("/v1/auth/password/forgot", json={"email": "nobody@email.com"})).status_code == 202
    assert (await anonymous.post("/v1/auth/password/forgot", json={"email": FIRST_USER["email"]})).status_code == 202
    token = _token_from_last_email(mock_autosend)

    reset = await anonymous.post("/v1/auth/password/reset", json={"token": token, "newPassword": "Brand-New-Pass-1"})
    assert reset.status_code == 204
    reused = await anonymous.post("/v1/auth/password/reset", json={"token": token, "newPassword": "Another-Pass-2"})
    assert reused.json()["code"] == "invalid_or_expired_token"

    assert (await anonymous.post("/v1/auth/signin", json=FIRST_USER)).status_code == 401
    assert (
        await anonymous.post("/v1/auth/signin", json={**FIRST_USER, "password": "Brand-New-Pass-1"})
    ).status_code == 200
    anonymous.cookies.clear()
    anonymous.cookies.set(config.AUTH_COOKIE_NAME, old_access)
    assert (await anonymous.get("/v2/user/me")).json()["code"] == "token_revoked"


async def test_email_verification_flow(client: Any, mock_autosend: Any) -> None:
    """Integration test verifying sign-up sends a verification link that marks the email as verified."""
    anonymous = await client()
    credentials = {"email": "verify_me@email.com", "password": "Verify-Pass-123"}
    assert (await anonymous.post("/v1/auth/signup", json=credentials)).status_code == 201
    token = _token_from_last_email(mock_autosend)
    assert (await anonymous.post("/v1/auth/verify-email", json={"token": token})).status_code == 204
    api_client = await client(**credentials)
    assert (await api_client.get("/v2/user/me")).json()["emailVerified"] is True


async def test_mfa_enrolment_and_signin(client: Any) -> None:
    """Integration test verifying TOTP enrolment, the MFA sign-in challenge and code verification."""
    api_client = await client(**FIRST_USER)
    setup = (await api_client.post("/v1/auth/mfa/setup")).json()
    totp = pyotp.TOTP(setup["secret"])
    assert (await api_client.post("/v1/auth/mfa/enable", json={"code": totp.now()})).status_code == 204

    anonymous = await client()
    challenge = (await anonymous.post("/v1/auth/signin", json=FIRST_USER)).json()
    assert challenge["mfaRequired"] is True
    assert config.AUTH_COOKIE_NAME not in anonymous.cookies
    wrong = await anonymous.post("/v1/auth/mfa/verify", json={"mfaToken": challenge["mfaToken"], "code": "000000"})
    assert wrong.json()["code"] == "invalid_mfa_code"
    ok = await anonymous.post("/v1/auth/mfa/verify", json={"mfaToken": challenge["mfaToken"], "code": totp.now()})
    assert ok.status_code == 204
    assert (await anonymous.get("/v2/user/me")).json()["mfaEnabled"] is True


async def test_admin_endpoint_requires_permission(client: Any) -> None:
    """Integration test verifying RBAC: regular users get 403 on admin endpoints."""
    api_client = await client(**FIRST_USER)
    response = await api_client.get("/v2/users/")
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_failed_signin_is_audited_despite_401(client: Any) -> None:
    """Integration test verifying failed sign-ins are written to the audit log although the request fails."""
    from sqlalchemy import select

    from app.main import db
    from app.modules.audit.infrastructure.persistence.models import AuditLogs

    api_client = await client()
    await api_client.post("/v1/auth/signin", json={"email": "ghost@email.com", "password": "nope-nope"})
    async with db.session_scope() as session:
        rows = (await session.execute(select(AuditLogs).where(AuditLogs.action == "auth.signin.failed"))).scalars()
        entry = next(iter(rows))
    assert entry.outcome == "failure"
    assert entry.details == {"reason": "unknown_email"}
    assert entry.ip_address is not None


async def test_audit_log_endpoint_requires_permission(client: Any) -> None:
    """Integration test verifying regular users cannot read the audit trail."""
    api_client = await client(**FIRST_USER)
    assert (await api_client.get("/v2/audit-logs/")).status_code == 403
