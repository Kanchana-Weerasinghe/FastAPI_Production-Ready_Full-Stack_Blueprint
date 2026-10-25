"""
UserAccount acceptance cases (QA-owned, black-box): only the published HTTP API and its OpenAPI contract.
Every test creates its own users through the API, so the suite can run against any environment.
"""

from collections.abc import Callable

import pytest

from tests.support.api import ApiSession, Credentials, unique_credentials
from tests.support.contract import Contract
from tests.support.settings import Settings

pytestmark = pytest.mark.usefixtures("system_under_test")

PUBLIC_PROFILE_FIELDS = {"id", "email", "username", "role", "emailVerified", "mfaEnabled"}


@pytest.mark.br("BR-01", "TC-01-5")
def test_br_01_sign_up_with_invalid_email_is_rejected(session: Callable[[], ApiSession], contract: Contract) -> None:
    response = session().http.post("/v1/auth/signup", json={"email": "not-an-email", "password": "SecurePass123!"})
    contract.check(response, "POST", "/v1/auth/signup")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


@pytest.mark.br("BR-05", "TC-05-1")
def test_br_05_duplicate_email_does_not_create_a_second_account(
    session: Callable[[], ApiSession], new_user: Credentials, contract: Contract
) -> None:
    api = session()
    duplicate = api.http.post("/v1/auth/signup", json={"email": new_user.email, "password": "AnotherPass123!"})
    contract.check(duplicate, "POST", "/v1/auth/signup")
    assert duplicate.status_code == 201  # same answer as a new sign-up: no account enumeration
    assert api.sign_in(new_user).status_code == 200
    replaced = session().sign_in(Credentials(new_user.email, "AnotherPass123!"))
    assert replaced.status_code == 401


@pytest.mark.br("BR-07", "TC-07-6")
def test_br_07_enabling_mfa_before_setup_is_rejected(
    session: Callable[[], ApiSession], new_user: Credentials, contract: Contract
) -> None:
    api = session()
    api.sign_in(new_user)
    response = api.http.post("/v1/auth/mfa/enable", json={"code": "123456"})
    contract.check(response, "POST", "/v1/auth/mfa/enable")
    assert response.status_code == 400
    assert response.json()["code"] == "mfa_not_started"


@pytest.mark.br("BR-09", "TC-09-3")
def test_br_09_locked_account_cannot_sign_in_even_with_correct_password(
    session: Callable[[], ApiSession], new_user: Credentials, settings: Settings
) -> None:
    api = session()
    for _ in range(settings.login_max_failed_attempts):
        wrong = api.sign_in(Credentials(new_user.email, "wrong-password"))
        assert wrong.json()["code"] == "invalid_credentials"
    locked = api.sign_in(new_user)
    assert locked.status_code == 401
    assert locked.json()["code"] == "account_locked"


@pytest.mark.br("BR-10", "TC-10-2")
def test_br_10_user_deletes_own_account_and_is_signed_out(
    session: Callable[[], ApiSession], new_user: Credentials, settings: Settings, contract: Contract
) -> None:
    api = session()
    api.sign_in(new_user)
    response = api.http.delete("/v2/user/me")
    contract.check(response, "DELETE", "/v2/user/me")
    assert response.status_code == 204
    expired = [c for c in response.headers.get_list("set-cookie") if c.startswith(f"{settings.access_cookie}=")]
    assert expired, "the access-token cookie must be expired"
    assert "Max-Age=0" in expired[0]
    assert api.http.get("/v2/user/me").status_code == 401
    assert session().sign_in(new_user).status_code == 401  # the account no longer exists


@pytest.mark.br("BR-11", "TC-11-1")
def test_br_11_user_sees_own_profile_without_secrets(
    session: Callable[[], ApiSession], new_user: Credentials, contract: Contract
) -> None:
    api = session()
    api.sign_in(new_user)
    response = api.http.get("/v2/user/me")
    contract.check(response, "GET", "/v2/user/me")
    assert response.status_code == 200
    assert response.json()["email"] == new_user.email
    assert set(response.json()) == PUBLIC_PROFILE_FIELDS  # no password hash, MFA secret or lock data


@pytest.mark.br("BR-11", "TC-11-2")
def test_br_11_profile_requires_a_session(session: Callable[[], ApiSession], contract: Contract) -> None:
    response = session().http.get("/v2/user/me")
    contract.check(response, "GET", "/v2/user/me")
    assert response.status_code == 401


@pytest.mark.br("BR-11", "TC-11-3")
def test_br_11_normal_user_cannot_list_users(
    session: Callable[[], ApiSession], new_user: Credentials, contract: Contract
) -> None:
    api = session()
    api.sign_in(new_user)
    response = api.http.get("/v2/users/")
    contract.check(response, "GET", "/v2/users/")
    assert response.status_code == 403


@pytest.mark.br("BR-11", "TC-11-4")
def test_br_11_admin_can_list_users(session: Callable[[], ApiSession], admin: Credentials, contract: Contract) -> None:
    api = session()
    assert api.sign_in(admin).status_code == 200, "set QA_ADMIN_EMAIL / QA_ADMIN_PASSWORD for this environment"
    response = api.http.get("/v2/users/")
    contract.check(response, "GET", "/v2/users/")
    assert response.status_code == 200
    assert response.json()["founds"]


@pytest.mark.br("BR-11", "TC-11-5")
def test_br_11_admin_view_is_paginated_and_shows_admin_fields(
    session: Callable[[], ApiSession], admin: Credentials, contract: Contract
) -> None:
    for _ in range(2):  # make sure there are at least two users to page through
        session().http.post("/v1/auth/signup", json=unique_credentials().as_json())
    api = session()
    api.sign_in(admin)
    response = api.http.get("/v2/users/", params={"pageSize": 1})
    contract.check(response, "GET", "/v2/users/")
    assert response.status_code == 200
    body = response.json()
    assert len(body["founds"]) == 1
    assert {"createdAt", "lockedUntil"} <= set(body["founds"][0])
    assert body["searchOptions"]["totalCount"] >= 2
