"""
Shared test fixtures, named like the identity service's (the generate-test-suite skill copies its patterns).

- PostgreSQL runs in a throwaway Testcontainers container (Docker required), configured BEFORE any app
  module is imported, because settings are read at import.
- `client`: `await client()` is anonymous; `await client(user_id=..., role=...)` sends a bearer token like
  the ones the identity service issues (role defaults to "user").
- `grant_access(*operation_ids)` / `deny_access()`: replace the access document for one test; the real
  `require_access()` check still runs.
- `db_session`: a session inside a transaction rolled back after the test (repository tests).
- `fake_uow`: an in-memory UnitOfWork that records after-commit callbacks (`await fake_uow.commit()` runs them).

Integration tests also import `isolated_app_transaction` from tests/integrations/conftest.py.
"""

import os
import sys
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from testcontainers.postgres import PostgresContainer

from tests._database_safety import reject_external_test_database

TEST_JWT_SECRET = "test-secret-key-that-is-at-least-32-characters-long"
_postgres_container: PostgresContainer | None = None


def _configure_test_database() -> None:
    global _postgres_container
    reject_external_test_database(os.environ)
    if sys.platform == "win32":
        # Ryuk's port mapping is unreliable on Docker Desktop for Windows; the container is
        # stopped explicitly in `pytest_sessionfinish` instead.
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    _postgres_container = PostgresContainer(
        "postgres:16-alpine", username="test", password="test", dbname="app_test", driver=None
    )
    _postgres_container.start()
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "DB_HOST": _postgres_container.get_container_host_ip(),
            "DB_PORT": str(_postgres_container.get_exposed_port(5432)),
            "DB_USERNAME": "test",
            "DB_PASSWORD": "test",
            "DB_NAME": "app_test",
            "JWT_SECRET_KEY": TEST_JWT_SECRET,
            "RATE_LIMIT_ENABLED": "false",
        }
    )


_configure_test_database()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _postgres_container is not None:
        _postgres_container.stop()


import jwt
from httpx import ASGITransport, AsyncClient
from platform_kit.access import ANONYMOUS_ROLE, load_access_policy
from platform_kit.access.testing import AccessOverride, override_access
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import config
from app.main import app as app_instance
from app.models import Base
from tests.mocks.uow import FakeUnitOfWork

ClientFactory = Callable[..., Awaitable[AsyncClient]]

engine = create_async_engine(
    config.database_url,
    connect_args={"server_settings": {"search_path": config.DB_SCHEMA, "timezone": "UTC"}},
)


def access_token(*, user_id: uuid.UUID | None = None, role: str = "user") -> str:
    """An access token shaped like the identity service's, signed with the test secret."""
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id or uuid.uuid4()),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{config.DB_SCHEMA}"'))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[ClientFactory, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app_instance, raise_app_exceptions=False),
        base_url="http://localhost",
    ) as client_instance:

        async def _client(*, user_id: uuid.UUID | None = None, role: str | None = None) -> AsyncClient:
            client_instance.headers.pop("Authorization", None)
            if user_id is not None or role is not None:
                token = access_token(user_id=user_id, role=role or "user")
                client_instance.headers["Authorization"] = f"Bearer {token}"
            return client_instance

        yield _client


# --- Access control: replace the access document for one test; the real `require_access` still runs ---


@pytest.fixture
def _access_override() -> Iterator[AccessOverride]:
    # Public endpoints stay open, so anonymous calls behave as in production.
    document = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    public = document.role_operations.get(ANONYMOUS_ROLE, frozenset())
    with override_access(app_instance, service=config.SERVICE_NAME, public=public) as access:
        yield access


@pytest.fixture
def grant_access(_access_override: AccessOverride) -> Callable[..., None]:
    """`grant_access("listThings", ...)`: the signed-in test caller may call exactly these operationIds."""
    return _access_override.grant


@pytest.fixture
def deny_access(_access_override: AccessOverride) -> Callable[[], None]:
    """`deny_access()`: the signed-in test caller may call nothing (public endpoints stay open)."""
    return _access_override.deny


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session wrapped in a transaction that is rolled back after each test."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()
