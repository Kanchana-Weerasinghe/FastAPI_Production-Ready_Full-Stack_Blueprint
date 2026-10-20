"""Optimistic concurrency over HTTP: `ETag: W/"<version>"` on reads, `If-Match` on writes."""

from fastapi import Response

from platform_kit.errors import PreconditionFailedError


def etag_for(version: int) -> str:
    return f'W/"{version}"'


def set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = etag_for(version)


def check_if_match(if_match: str | None, current_version: int) -> None:
    """No header: unconditional write. Header present: it must match the current version."""
    if if_match is None:
        return
    expected = etag_for(current_version)
    candidates = {tag.strip() for tag in if_match.split(",")}
    if "*" in candidates or expected in candidates or expected.removeprefix("W/") in candidates:
        return
    raise PreconditionFailedError(
        "The resource was modified by someone else; reload it and retry", extra={"current_etag": expected}
    )


def expected_version(if_match: str | None) -> int | None:
    """Turns `If-Match: W/"3"` into 3 for use cases that take an expected version; `*`/absent -> None."""
    if if_match is None or if_match.strip() == "*":
        return None
    tag = if_match.split(",")[0].strip().removeprefix("W/").strip('"')
    if not tag.isdigit():
        raise PreconditionFailedError("If-Match must be an ETag returned by this API")
    return int(tag)
