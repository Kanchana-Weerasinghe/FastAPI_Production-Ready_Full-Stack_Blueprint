"""
API TESTS: the real endpoints with the real database (Testcontainers) and the real access check.

Fixtures (tests/conftest.py): `client()` anonymous, `client(user_id=...)` signed in;
`grant_access("operationId", ...)` / `deny_access()` replace config/access-control.json for one test.
Every test is rolled back afterwards (`isolated_app_transaction`).
"""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from httpx import AsyncClient

from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

BASE = "/v1/items"
ClientFactory = Callable[..., Awaitable[AsyncClient]]
ALL_OPERATIONS = (
    "createItem",
    "listItems",
    "getItem",
    "updateItem",
    "archiveItem",
    "restoreItem",
    "deleteItem",
)


async def test_sign_in_is_required(client: ClientFactory) -> None:
    http = await client()
    assert (await http.get(f"{BASE}/")).status_code == 401


async def test_caller_without_a_grant_is_refused(client: ClientFactory, deny_access: Callable[[], None]) -> None:
    deny_access()
    http = await client(user_id=uuid4())
    response = await http.get(f"{BASE}/")
    assert response.status_code == 403
    assert response.json()["code"] == "access_denied"


async def test_full_lifecycle(client: ClientFactory, grant_access: Callable[..., None]) -> None:
    grant_access(*ALL_OPERATIONS)
    http = await client(user_id=uuid4())

    created = await http.post(f"{BASE}/", json={"name": "Blue pen", "code": "itm-001"})  # create
    assert created.status_code == 201, created.text
    item = created.json()
    assert (item["code"], item["status"]) == ("ITM-001", "active")
    url = f"{BASE}/{ item['id'] }"
    assert created.headers["Location"] == url

    assert (await http.get(url)).status_code == 200  # get
    assert (await http.get(f"{BASE}/", params={"status": "active"})).json()["pageInfo"]["totalCount"] == 1  # list

    renamed = await http.patch(url, json={"name": "Red pen"})  # update
    assert renamed.json()["name"] == "Red pen"

    still_active = await http.delete(url)  # entity rule: archive first
    assert still_active.status_code == 409
    assert still_active.json()["code"] == "invalid_item_state"

    archived = await http.post(f"{url}:archive")  # archive
    assert archived.json()["status"] == "archived"
    blocked = await http.patch(url, json={"name": "Green pen"})  # entity rule: archived cannot change
    assert blocked.status_code == 409

    restored = await http.post(f"{url}:restore")  # restore
    assert restored.json()["status"] == "active"

    await http.post(f"{url}:archive")
    assert (await http.delete(url)).status_code == 204  # delete
    gone = await http.get(url)
    assert gone.status_code == 404
    assert gone.json()["code"] == "item_not_found"


async def test_duplicate_code_is_a_409(client: ClientFactory, grant_access: Callable[..., None]) -> None:
    grant_access(*ALL_OPERATIONS)
    http = await client(user_id=uuid4())
    await http.post(f"{BASE}/", json={"name": "Blue pen", "code": "ITM-001"})
    response = await http.post(f"{BASE}/", json={"name": "Red pen", "code": "itm-001"})
    assert response.status_code == 409
    assert response.json()["code"] == "item_code_taken"


async def test_invalid_code_is_a_422(client: ClientFactory, grant_access: Callable[..., None]) -> None:
    grant_access(*ALL_OPERATIONS)
    http = await client(user_id=uuid4())
    response = await http.post(f"{BASE}/", json={"name": "Blue pen", "code": "ITM 001"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_item_code"
