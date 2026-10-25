import uuid
from typing import Any

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}


async def test_idempotency_key_replays_response(client: Any) -> None:
    """Integration test verifying a retried POST with the same Idempotency-Key is replayed, not executed twice."""
    from sqlalchemy import func, select

    from app.main import db
    from app.modules.users.infrastructure.persistence.models import Users

    api_client = await client()
    key = {"Idempotency-Key": str(uuid.uuid4())}
    body = {"email": f"idem_{uuid.uuid4().hex[:8]}@example.com", "password": "SecurePass123!"}

    first = await api_client.post("/v1/auth/signup", json=body, headers=key)
    retry = await api_client.post("/v1/auth/signup", json=body, headers=key)
    assert first.status_code == retry.status_code == 201
    assert retry.headers["idempotent-replayed"] == "true"
    async with db.session_scope() as session:
        count = (await session.execute(select(func.count()).where(Users.email == body["email"]))).scalar_one()
    assert count == 1

    reused = await api_client.post("/v1/auth/signup", json={**body, "password": "OtherPass123!"}, headers=key)
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
