from collections.abc import Callable, Iterator

import httpx
import pytest

from tests.support.api import ApiSession, Credentials, unique_credentials
from tests.support.contract import Contract
from tests.support.settings import Settings, load_settings


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "br(rule_id, case_id): links a test to a business rule and test case")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def system_under_test(settings: Settings) -> None:
    """Fail fast with a clear message when the service is not reachable."""
    try:
        httpx.get(f"{settings.base_url}/health/live", timeout=5.0).raise_for_status()
    except httpx.HTTPError as e:
        pytest.exit(f"Identity service not reachable at {settings.base_url}: {e}", returncode=2)


@pytest.fixture(scope="session")
def contract(settings: Settings) -> Contract:
    return Contract(settings.openapi_path)


@pytest.fixture
def session(settings: Settings) -> Iterator[Callable[[], ApiSession]]:
    """Factory for independent API sessions (each with its own cookie jar)."""
    opened: list[ApiSession] = []

    def open_session() -> ApiSession:
        api = ApiSession(settings)
        opened.append(api)
        return api

    yield open_session
    for api in opened:
        api.close()


@pytest.fixture
def new_user(session: Callable[[], ApiSession]) -> Credentials:
    """A fresh account created through the public API, so tests never share or corrupt state."""
    credentials = unique_credentials()
    response = session().http.post("/v1/auth/signup", json=credentials.as_json())
    assert response.status_code == 201, response.text
    return credentials


@pytest.fixture
def admin(settings: Settings) -> Credentials:
    return Credentials(email=settings.admin_email, password=settings.admin_password)
