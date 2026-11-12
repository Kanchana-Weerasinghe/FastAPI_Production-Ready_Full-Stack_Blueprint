"""
Integration tests for central access control (docs/adr/0017-central-access-control.md): the real
`require_access` runs; `grant_access` / `deny_access` only replace the access document.
"""

from collections.abc import Callable
from typing import Any

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}


async def test_granted_operation_is_allowed_for_a_regular_user(client: Any, grant_access: Callable[..., None]) -> None:
    """Granting `listUsers` lets a regular user list users: the decision is data, not the role in code."""
    grant_access("listUsers")
    api_client = await client(**FIRST_USER)
    assert (await api_client.get("/v2/users/")).status_code == 200


async def test_operation_not_granted_is_refused_with_access_denied(
    client: Any, grant_access: Callable[..., None]
) -> None:
    """Only the granted operations are allowed; everything else is 403 `access_denied`."""
    grant_access("listUsers")
    api_client = await client(**FIRST_USER)
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 403
    assert response.json()["code"] == "access_denied"


async def test_deny_access_refuses_everything_but_public_endpoints(
    client: Any, deny_access: Callable[[], None]
) -> None:
    """With nothing granted the user can still sign in (public), but nothing else."""
    deny_access()
    api_client = await client(**FIRST_USER)  # signs in: public endpoints stay open
    assert (await api_client.get("/v2/user/me")).status_code == 403


async def test_unauthenticated_caller_still_gets_401(client: Any, grant_access: Callable[..., None]) -> None:
    """Granting an operation never opens it to callers who are not signed in."""
    grant_access("getCurrentUser")
    api_client = await client()
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


async def test_my_access_lists_the_callers_roles_and_operations(client: Any) -> None:
    """`GET /v1/access/me` returns what the access document grants the caller (here: a regular user)."""
    api_client = await client(**FIRST_USER)
    response = await api_client.get("/v1/access/me")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "identity"
    assert body["roles"] == ["user"]
    assert {"getCurrentUser", "getMyAccess", "signIn"} <= set(body["operations"])
    assert "listUsers" not in body["operations"]
