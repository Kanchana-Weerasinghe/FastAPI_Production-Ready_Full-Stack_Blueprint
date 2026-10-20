"""
HTTP conditional requests for optimistic concurrency (RFC 9110 §13).

GET responses carry `ETag: W/"<version>"`; clients send it back in `If-Match` on PATCH/PUT/DELETE.
If the resource changed in the meantime the request fails with 412 instead of silently overwriting
someone else's update ("lost update" problem).
"""

import re

from fastapi import Response

from .errors import BadRequestError, PreconditionFailedError

_ETAG = re.compile(r'^(W/)?"(\d+)"$')


def etag_for(version: int) -> str:
    return f'W/"{version}"'


def set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = etag_for(version)


def check_if_match(if_match: str | None, current_version: int) -> None:
    """Raises 412 when an `If-Match` header is present and does not match `current_version`."""
    if if_match is None or if_match.strip() == "*":
        return
    candidates = [tag.strip() for tag in if_match.split(",")]
    versions = []
    for tag in candidates:
        match = _ETAG.match(tag)
        if not match:
            raise BadRequestError("Malformed If-Match header", code="invalid_if_match")
        versions.append(int(match.group(2)))
    if current_version not in versions:
        raise PreconditionFailedError(
            "The resource has changed since you loaded it. Reload and try again.",
            extra={"current_etag": etag_for(current_version)},
        )
