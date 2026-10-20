import uuid
from typing import Any

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}


async def _first_todo_id(api_client: Any) -> str:
    return str((await api_client.get("/v2/todos/")).json()["founds"][0]["id"])


async def test_etag_and_if_match_prevent_lost_updates(client: Any) -> None:
    """Integration test verifying GET returns an ETag and PATCH with a stale If-Match fails with 412."""
    api_client = await client(**FIRST_USER)
    todo_id = await _first_todo_id(api_client)
    detail = await api_client.get(f"/v2/todos/{todo_id}")
    etag = detail.headers["etag"]
    assert etag == f'W/"{detail.json()["version"]}"'

    first = await api_client.patch(f"/v2/todos/{todo_id}", json={"title": "A"}, headers={"If-Match": etag})
    assert first.status_code == 200
    assert first.headers["etag"] != etag

    stale = await api_client.patch(f"/v2/todos/{todo_id}", json={"title": "B"}, headers={"If-Match": etag})
    assert stale.status_code == 412
    assert stale.json()["code"] == "precondition_failed"
    assert stale.json()["current_etag"] == first.headers["etag"]


async def test_idempotency_key_replays_response(client: Any) -> None:
    """Integration test verifying a retried POST with the same Idempotency-Key is replayed, not executed twice."""
    api_client = await client(**FIRST_USER)
    key = {"Idempotency-Key": str(uuid.uuid4())}
    before = (await api_client.get("/v2/todos/")).json()["searchOptions"]["totalCount"]

    first = await api_client.post("/v2/todos/", json={"title": "Once"}, headers=key)
    retry = await api_client.post("/v2/todos/", json={"title": "Once"}, headers=key)
    assert first.status_code == retry.status_code == 201
    assert retry.headers["idempotent-replayed"] == "true"
    assert (await api_client.get("/v2/todos/")).json()["searchOptions"]["totalCount"] == before + 1

    reused = await api_client.post("/v2/todos/", json={"title": "Different"}, headers=key)
    assert reused.status_code == 422
    assert reused.json()["code"] == "idempotency_key_reused"


async def test_audit_log_cursor_pagination(client: Any) -> None:
    """Integration test verifying keyset pagination returns disjoint pages and rejects malformed cursors with 400."""
    from sqlalchemy import update

    from app.main import db
    from app.modules.users.infrastructure.persistence.models import Users

    async with db.session_scope() as session:
        await session.execute(update(Users).where(Users.email == FIRST_USER["email"]).values(role="admin"))
    admin = await client(**FIRST_USER)
    for _ in range(2):
        await admin.post("/v1/auth/signout-all")
        admin = await client(**FIRST_USER)

    first = (await admin.get("/v2/audit-logs/", params={"limit": 2})).json()
    assert len(first["items"]) == 2
    assert first["nextCursor"]
    second = (await admin.get("/v2/audit-logs/", params={"limit": 2, "cursor": first["nextCursor"]})).json()
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})

    bad = await admin.get("/v2/audit-logs/", params={"cursor": "not-a-cursor"})
    assert bad.status_code == 400
    assert bad.json()["code"] == "invalid_cursor"
