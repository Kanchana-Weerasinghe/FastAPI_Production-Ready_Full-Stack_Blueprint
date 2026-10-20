from unittest.mock import MagicMock

import pytest
from fastapi import Request

from app.core.client_ip import get_real_ip_address
from app.core.config import config


def _request(peer: str | None, headers: dict[str, str]) -> MagicMock:
    request = MagicMock(spec=Request)
    request.headers = headers
    if peer is None:
        request.client = None
    else:
        request.client = MagicMock()
        request.client.host = peer
    return request


@pytest.fixture
def trusted_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "TRUSTED_PROXIES", "10.0.0.0/8")


def test_proxy_headers_ignored_from_untrusted_peer() -> None:
    """Test that a client connecting directly cannot spoof its IP through X-Forwarded-For or X-Real-IP."""
    request = _request("203.0.113.7", {"X-Forwarded-For": "1.2.3.4", "X-Real-IP": "5.6.7.8"})
    assert get_real_ip_address(request) == "203.0.113.7"


@pytest.mark.usefixtures("trusted_proxy")
def test_x_forwarded_for_from_trusted_proxy() -> None:
    """Test that the right-most untrusted X-Forwarded-For hop is used when the peer is a trusted proxy."""
    request = _request("10.0.0.2", {"X-Forwarded-For": "6.6.6.6, 1.2.3.4, 10.0.0.5"})
    assert get_real_ip_address(request) == "1.2.3.4"


@pytest.mark.usefixtures("trusted_proxy")
def test_x_real_ip_from_trusted_proxy() -> None:
    """Test that X-Real-IP is used when a trusted proxy sends it without X-Forwarded-For."""
    request = _request("10.0.0.2", {"X-Real-IP": "9.10.11.12"})
    assert get_real_ip_address(request) == "9.10.11.12"


@pytest.mark.usefixtures("trusted_proxy")
def test_trusted_proxy_without_headers() -> None:
    """Test that the peer address is returned when a trusted proxy sends no forwarding headers."""
    request = _request("10.0.0.2", {"X-Forwarded-For": "10.0.0.9"})
    assert get_real_ip_address(request) == "10.0.0.2"


def test_get_real_ip_from_client_host() -> None:
    """Test that request.client.host is used when proxy headers are absent."""
    assert get_real_ip_address(_request("192.168.1.1", {})) == "192.168.1.1"


def test_get_real_ip_unknown_client() -> None:
    """Test that 'unknown' is returned when the request has no client information."""
    assert get_real_ip_address(_request(None, {})) == "unknown"
