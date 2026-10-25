import os
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
from testcontainers.postgres import PostgresContainer

from tests._database_safety import reject_external_test_database

_postgres_container: PostgresContainer | None = None


def _configure_test_database() -> None:
    """
    Points the app at an ephemeral test database BEFORE any app module is imported.

    Tests recreate the database schema, so only a throwaway Postgres container is safe.
    """
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
    settings = {
        "DB_HOST": _postgres_container.get_container_host_ip(),
        "DB_PORT": str(_postgres_container.get_exposed_port(5432)),
        "DB_USERNAME": "test",
        "DB_PASSWORD": "test",
        "DB_NAME": "app_test",
    }
    os.environ.update(settings)
    os.environ.update(
        {
            "ENVIRONMENT": "staging",
            "APP_DOMAIN": "",
            "SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
            "FIELD_ENCRYPTION_KEY": "test-field-encryption-key-at-least-32-characters",
            "RATE_LIMIT_ENABLED": "false",
            # Deliver outbox events right after commit, so tests don't need the worker.
            "OUTBOX_INLINE_DISPATCH": "true",
            # The test client talks plain HTTP, which never sends Secure cookies back.
            "AUTH_COOKIE_SECURE_OVERRIDE": "false",
        }
    )


_configure_test_database()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _postgres_container is not None:
        _postgres_container.stop()


from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import config
from app.main import app as app_instance
from app.main import container
from app.modules.users.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.modules.users.public import UserUseCases
from app.shared.models import BaseModel
from app.shared.storage import LocalFileStorage
from tests.factories import load_test_data
from tests.mocks.audit import FakeAuditService
from tests.mocks.autosend import MockAutosendClient
from tests.mocks.uow import FakeUnitOfWork
from tests.mocks.user_repository import FakeUserRepository

engine = create_async_engine(
    url=config.SQLALCHEMY_DATABASE_URI,
    echo=config.SQLALCHEMY_ECHO,
    connect_args={"server_settings": {"search_path": config.DB_SCHEMA, "timezone": "UTC"}},
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    future=True,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def seed_database(setup_database: None) -> None:
    """Populate the database with mock data after tables are created successfully."""
    async_session = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        await load_test_data(session)
        await session.commit()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[Any, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app_instance, raise_app_exceptions=False),
        base_url="http://localhost",
    ) as client_instance:

        async def _client(email: str | None = None, password: str | None = None) -> AsyncClient:
            client_instance.cookies.clear()
            client_instance.headers.pop(config.CSRF_HEADER_NAME, None)
            if email and password:
                await client_instance.post(
                    "/v1/auth/signin",
                    json={"email": email, "password": password},
                )
                # Like the web app: echo the CSRF cookie in a header on unsafe requests.
                csrf_token = client_instance.cookies.get(config.CSRF_COOKIE_NAME)
                if csrf_token:
                    client_instance.headers[config.CSRF_HEADER_NAME] = csrf_token
            return client_instance

        yield _client


@pytest.fixture(scope="session", autouse=True)
def mock_autosend() -> Any:
    mock_client = MockAutosendClient()
    container.autosend_client.override(mock_client)
    yield mock_client
    container.autosend_client.reset_override()


@pytest.fixture
def mock_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def mock_autosend_client() -> MockAutosendClient:
    return MockAutosendClient()


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def user_use_cases(mock_user_repository: FakeUserRepository, fake_uow: FakeUnitOfWork) -> UserUseCases:
    return UserUseCases(
        user_repository=mock_user_repository, uow=fake_uow, storage=LocalFileStorage(), audit=FakeAuditService()
    )


@pytest.fixture(autouse=True)
def temp_upload_dir(tmp_path: Path) -> Generator[None, None, None]:
    """Temporary override of the uploads folder during tests to prevent cluttering."""
    old_upload_dir = config.UPLOAD_DIR
    config.UPLOAD_DIR = str(tmp_path / "uploads")
    yield
    config.UPLOAD_DIR = old_upload_dir


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


@pytest.fixture
def user_repository(db_session: AsyncSession) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db_session)
