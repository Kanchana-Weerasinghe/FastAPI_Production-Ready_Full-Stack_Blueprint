"""
Rate limiting: the same `rate_limit(...)` dependency as the identity service.

    @router.get("/", operation_id="listThings", dependencies=[rate_limit("200/minute")])

Limits count per client address. Set RATE_LIMIT_STORAGE_URI to Redis so they hold across gunicorn
workers and replicas; RATE_LIMIT_ENABLED=false turns them off (tests, the QA suite).
"""

from typing import Any

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import config

limiter = Limiter(key_func=get_remote_address, storage_uri=config.RATE_LIMIT_STORAGE_URI)


def rate_limit(limit_value: str) -> Any:
    """FastAPI dependency factory for rate limiting, e.g. `rate_limit("60/minute")`."""

    async def dependency(request: Request) -> None:
        pass

    if not config.RATE_LIMIT_ENABLED:
        return Depends(dependency)

    func_name = f"dependency_{id(dependency)}"
    dependency.__name__ = func_name
    dependency.__qualname__ = f"rate_limit.<locals>.{func_name}"
    return Depends(limiter.limit(limit_value)(dependency))
