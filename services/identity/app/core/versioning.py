"""
Deprecation signalling for API endpoints (see docs/adr/0003-api-versioning.md).

    @router.get("/old", dependencies=[deprecated(sunset=date(2027, 6, 30), link="https://docs.example.com/migrate")])

Responses then carry `Deprecation` (RFC 9745), `Sunset` (RFC 8594) and `Link; rel="deprecation"` headers,
and each call is logged so remaining usage can be tracked before removal.
"""

from datetime import UTC, date, datetime
from email.utils import format_datetime
from typing import Any

from fastapi import Depends, Request, Response

from .logging import logger


def deprecated(*, sunset: date, link: str | None = None, since: date | None = None) -> Any:
    sunset_http = format_datetime(datetime(sunset.year, sunset.month, sunset.day, tzinfo=UTC), usegmt=True)
    deprecation = f"@{int(datetime(since.year, since.month, since.day, tzinfo=UTC).timestamp())}" if since else "?1"

    async def dependency(request: Request, response: Response) -> None:
        response.headers["Deprecation"] = deprecation
        response.headers["Sunset"] = sunset_http
        if link:
            response.headers["Link"] = f'<{link}>; rel="deprecation"'
        logger.info("deprecated_endpoint_called", path=request.url.path, sunset=sunset.isoformat())

    return Depends(dependency)
