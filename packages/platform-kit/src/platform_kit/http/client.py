"""
Calling another domain service.

Use it only inside an infrastructure adapter that implements an application port, so use cases
never know a dependency is remote. The caller's token and request ID are forwarded, timeouts are
mandatory, and transport failures become `ServiceUnavailableError` (503) instead of a raw exception.
"""

from typing import Any

import httpx
import structlog

from platform_kit.errors import ServiceUnavailableError
from platform_kit.http.middleware import REQUEST_ID_HEADER


class ServiceClient:
    def __init__(self, *, base_url: str, service_name: str, timeout_seconds: float = 5.0) -> None:
        self.service_name = service_name
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def request(self, method: str, path: str, *, token: str | None = None, **kwargs: Any) -> httpx.Response:
        headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        if request_id:
            headers[REQUEST_ID_HEADER] = str(request_id)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            return await self._client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as e:
            raise ServiceUnavailableError(f"{self.service_name} is unavailable", code="dependency_unavailable") from e

    async def close(self) -> None:
        await self._client.aclose()
