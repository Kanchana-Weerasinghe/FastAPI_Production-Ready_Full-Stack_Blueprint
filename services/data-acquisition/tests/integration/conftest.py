"""
Integration tests run the real app against a throwaway PostgreSQL container, migrated with Alembic.

The container is configured BEFORE any app module is imported, because settings are read at import.
"""

import os
import sys
import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

SECRET = "integration-test-secret-key-at-least-32-chars"
SERVICE_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresContainer, None, None]:
    if "TEST_DB_HOST" in os.environ:
        pytest.exit("Integration tests only run against a disposable container; unset TEST_DB_HOST.", returncode=2)
    if sys.platform == "win32":
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    container = PostgresContainer(
        "postgres:16-alpine", username="test", password="test", dbname="app_test", driver=None
    )
    container.start()
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "DB_HOST": container.get_container_host_ip(),
            "DB_PORT": str(container.get_exposed_port(5432)),
            "DB_USERNAME": "test",
            "DB_PASSWORD": "test",
            "DB_NAME": "app_test",
            "JWT_SECRET_KEY": SECRET,
            "ACTIVE_JOB_LIMIT_PER_OWNER": "3",
        }
    )
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def migrated(postgres: PostgresContainer) -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(SERVICE_DIR / "alembic.ini")), "head")


@pytest.fixture(scope="session")
async def client(migrated: None) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


TokenFactory = Callable[..., dict[str, str]]


@pytest.fixture
def auth() -> TokenFactory:
    """Builds `Authorization` headers like the ones the identity service's access tokens produce."""

    def make(*, user_id: uuid.UUID | None = None, role: str = "user", **overrides: Any) -> dict[str, str]:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user_id or uuid.uuid4()),
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            **overrides,
        }
        return {"Authorization": f"Bearer {jwt.encode(claims, SECRET, algorithm='HS256')}"}

    return make
