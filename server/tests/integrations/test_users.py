from typing import Any
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.database import Database
from app.main import app, app_creator

FIRST_USER_CREDENTIALS = {"email": "first_user@email.com", "password": "SecurePass123!"}


async def test_get_me_success(client: Any) -> None:
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 200
    assert response.json()["email"] == FIRST_USER_CREDENTIALS["email"]


async def test_get_me_unauthorized(client: Any) -> None:
    api_client = await client()
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 401


async def test_delete_me_success(client: Any) -> None:
    """Test that the delete me endpoint returns 204 and the user is deleted."""
    base_client = await client()
    await base_client.post("/v1/auth/signup", json={"email": "delete_me@email.com", "password": "SecurePass123!"})
    api_client = await client("delete_me@email.com", "SecurePass123!")
    response = await api_client.delete("/v2/user/me")
    assert response.status_code == 204
    response = await api_client.get("/v2/user/me")
    assert response.status_code == 401


async def test_delete_me_unauthorized(client: Any) -> None:
    """Test that the delete me endpoint returns 401 for unauthorized users."""
    api_client = await client()
    response = await api_client.delete("/v2/user/me")
    assert response.status_code == 401


async def test_health_check_success(client: Any) -> None:
    """Test that the readiness endpoints return 200 with the database check, and liveness needs no dependencies."""
    api_client = await client()
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
    assert (await api_client.get("/health/ready")).status_code == 200
    assert (await api_client.get("/health/live")).json() == {"status": "alive"}


async def test_health_check_database_error(client: Any) -> None:
    """Test that the /health endpoint returns 503 when the database raises an exception."""
    api_client = await client()
    with patch.object(AsyncSession, "execute") as mock_execute:
        mock_execute.side_effect = Exception("DB Connection Refused")
        response = await api_client.get("/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Database connection failed"


async def test_app_lifespan() -> None:
    """Test the application lifespan setup and tear down."""
    with patch.object(app_creator.db, "close", new_callable=AsyncMock) as mock_close:
        async with app_creator.lifespan(app):
            pass
        mock_close.assert_called_once()


async def test_database_close_and_session_context() -> None:
    """Test Database.close and the fallback path in _get_session_context."""
    db = Database(
        url=config.SQLALCHEMY_DATABASE_URI,
        echo=config.SQLALCHEMY_ECHO,
        search_path=config.DB_SCHEMA,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
    )
    db.scoped_session()
    await db.scoped_session.remove()
    await db.close()


async def test_metrics_endpoint_exposes_red_and_backlog_metrics(client: Any, monkeypatch: Any) -> None:
    """Test that /metrics exposes request metrics by route template plus outbox gauges, and honours METRICS_TOKEN."""
    from pydantic import SecretStr

    api_client = await client()
    await api_client.get("/health/live")
    body = (await api_client.get("/metrics")).text
    assert 'http_requests_total{method="GET",route="/health/live",status="200"}' in body
    assert "outbox_pending_events" in body
    assert "db_pool_connections_in_use" in body

    monkeypatch.setattr(config, "METRICS_TOKEN", SecretStr("scrape-secret"))
    assert (await api_client.get("/metrics")).status_code == 401
    invalid = await api_client.get("/metrics", headers={"Authorization": "Bearer wrong-secret"})
    assert invalid.status_code == 401
    ok = await api_client.get("/metrics", headers={"Authorization": "Bearer scrape-secret"})
    assert ok.status_code == 200
