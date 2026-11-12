from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

ClientFactory = Callable[..., Awaitable[AsyncClient]]


async def test_service_is_live(client: ClientFactory) -> None:
    http = await client()
    response = await http.get("/health/live")
    assert response.status_code == 200


async def test_service_is_ready_with_its_database(client: ClientFactory) -> None:
    http = await client()
    response = await http.get("/health/ready")
    assert response.status_code == 200
