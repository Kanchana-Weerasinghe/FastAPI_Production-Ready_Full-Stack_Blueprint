import uuid
from typing import Any

from sqlalchemy import update

from app.main import db
from app.modules.flags.domain.entities import FeatureFlagState
from app.modules.flags.service import FeatureFlagService, bucket
from app.modules.users.infrastructure.persistence.models import Users

FIRST_USER = {"email": "first_user@email.com", "password": "SecurePass123!"}


def _flag(**overrides: Any) -> FeatureFlagState:
    values: dict[str, Any] = {"key": "beta", "enabled": True, "rollout_percentage": 100, "roles": []}
    values.update(overrides)
    return FeatureFlagState(description="", **values)


def test_flag_evaluation_rules() -> None:
    """Test that disabled flags are off, role targeting wins, and percentage rollout is deterministic per user."""
    user_id = uuid.uuid4()
    assert FeatureFlagService.evaluate(None, user_id, "user") is False
    assert FeatureFlagService.evaluate(_flag(enabled=False), user_id, "admin") is False
    assert FeatureFlagService.evaluate(_flag(rollout_percentage=0, roles=["admin"]), user_id, "admin") is True
    assert FeatureFlagService.evaluate(_flag(rollout_percentage=0), user_id, "user") is False
    in_bucket = _flag(rollout_percentage=bucket("beta", user_id) + 1)
    out_of_bucket = _flag(rollout_percentage=bucket("beta", user_id))
    assert FeatureFlagService.evaluate(in_bucket, user_id, "user") is True
    assert FeatureFlagService.evaluate(out_of_bucket, user_id, "user") is False


async def test_flags_admin_and_evaluation(client: Any) -> None:
    """Integration test verifying admins manage flags (audited) and users get their evaluated flags."""
    user = await client(**FIRST_USER)
    assert (await user.put("/v2/feature-flags/new-editor", json={"enabled": True})).status_code == 403

    async with db.session_scope() as session:
        await session.execute(update(Users).where(Users.email == FIRST_USER["email"]).values(role="admin"))
    admin = await client(**FIRST_USER)
    await admin.post("/v1/auth/signout-all")
    admin = await client(**FIRST_USER)

    response = await admin.put("/v2/feature-flags/new-editor", json={"enabled": True, "rolloutPercentage": 100})
    assert response.status_code == 200
    assert response.json()["key"] == "new-editor"
    assert (await admin.get("/v2/feature-flags/me")).json()["flags"]["new-editor"] is True
    assert (await admin.put("/v2/feature-flags/Bad Key!", json={})).status_code == 422


async def test_data_export_contains_user_data(client: Any) -> None:
    """Integration test verifying the data export is a downloadable JSON with profile, todos and security events."""
    api_client = await client(**FIRST_USER)
    response = await api_client.get("/v2/user/me/export")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    data = response.json()
    assert data["profile"]["email"] == FIRST_USER["email"]
    assert len(data["todos"]) == 31
    assert any(event["action"] == "auth.signin.succeeded" for event in data["security_events"])
