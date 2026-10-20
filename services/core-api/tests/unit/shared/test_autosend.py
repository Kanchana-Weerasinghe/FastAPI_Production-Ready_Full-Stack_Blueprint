from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import config
from app.shared.http import CircuitBreaker, CircuitOpenError, ResilientHttpClient
from app.shared.integrations.autosend import AutosendClient


def _response(status: int, body: dict[str, object] | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = body or {}
    response.text = ""
    return response


@pytest.fixture(autouse=True)
def no_backoff_sleep() -> object:
    with patch("app.shared.http.asyncio.sleep", new=AsyncMock()) as sleep:
        yield sleep


@patch("app.shared.http.httpx.AsyncClient")
async def test_send_email_success(mock_client_class: MagicMock) -> None:
    """Test that send_email returns True when Autosend answers 200 with success=True."""
    mock_client_class.return_value.request = AsyncMock(return_value=_response(200, {"success": True}))
    assert await AutosendClient().send_email("a@b.c", "Hi", "<p>Hi</p>") is True


@patch("app.shared.http.httpx.AsyncClient")
async def test_send_email_rejected(mock_client_class: MagicMock) -> None:
    """Test that send_email returns False (no exception) when Autosend rejects the message."""
    mock_client_class.return_value.request = AsyncMock(return_value=_response(200, {"success": False}))
    assert await AutosendClient().send_email("a@b.c", "Hi", "<p>Hi</p>") is False


@patch("app.shared.http.httpx.AsyncClient")
async def test_retries_transient_errors_then_succeeds(mock_client_class: MagicMock) -> None:
    """Test that connection errors and 503s are retried with backoff before succeeding."""
    mock_client_class.return_value.request = AsyncMock(
        side_effect=[httpx.ConnectError("boom"), _response(503), _response(200)]
    )
    response = await ResilientHttpClient("upstream").get("/x")
    assert response.status_code == 200
    assert mock_client_class.return_value.request.await_count == 3


@patch("app.shared.http.httpx.AsyncClient")
async def test_post_is_not_retried_by_default(mock_client_class: MagicMock) -> None:
    """Test that non-idempotent requests are not retried unless explicitly allowed."""
    mock_client_class.return_value.request = AsyncMock(return_value=_response(503))
    response = await ResilientHttpClient("upstream").post("/x")
    assert response.status_code == 503
    assert mock_client_class.return_value.request.await_count == 1


def test_circuit_breaker_opens_and_half_opens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the breaker fails fast after the threshold and allows a trial call after the reset period."""
    breaker = CircuitBreaker("upstream", failure_threshold=2, reset_seconds=30)
    breaker.record_failure()
    breaker.before_call()
    breaker.record_failure()
    with pytest.raises(CircuitOpenError):
        breaker.before_call()
    opened_at = breaker._opened_at
    assert opened_at is not None
    monkeypatch.setattr("app.shared.http.time.monotonic", lambda: opened_at + 31)
    assert breaker.state == "half_open"
    breaker.before_call()
    breaker.record_success()
    assert breaker.state == "closed"


def test_resilient_client_uses_configured_timeout() -> None:
    """Test that outbound requests always carry the configured timeout."""
    client = ResilientHttpClient("upstream")
    assert client.client.timeout.read == config.HTTP_TIMEOUT_SECONDS
