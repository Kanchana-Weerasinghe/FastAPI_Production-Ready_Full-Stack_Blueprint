"""
Where a service gets its access policy from (the port), and the adapters.

`JsonFileAccessLookup` reads the central JSON document today. When the access tables exist, an
adapter that fetches the policy from the identity service replaces it; nothing else changes.
"""

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from platform_kit.access.policy import AccessConfigError, AccessPolicy, parse_access_document
from platform_kit.logging import logger


class AccessLookup(ABC):
    """Port: returns the current access policy of this service."""

    @abstractmethod
    async def policy(self) -> AccessPolicy: ...

    def cached(self) -> AccessPolicy | None:
        """The policy already in memory, if any (used to validate the setup at startup)."""
        return None


class StaticAccessLookup(AccessLookup):
    """A fixed policy: tests and the `grant_access` / `deny_access` fixtures."""

    def __init__(self, policy: AccessPolicy) -> None:
        self._policy = policy

    async def policy(self) -> AccessPolicy:
        return self._policy

    def cached(self) -> AccessPolicy:
        return self._policy


def load_access_policy(path: str | Path, *, service: str) -> AccessPolicy:
    """Reads and validates the central document and returns this service's part of it."""
    file = Path(path)
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except OSError as e:
        raise AccessConfigError(f"Cannot read access document {file}: {e}") from e
    except json.JSONDecodeError as e:
        raise AccessConfigError(f"Access document {file} is not valid JSON: {e}") from e
    return AccessPolicy.for_service(parse_access_document(data), service)


class JsonFileAccessLookup(AccessLookup):
    """
    Loads the policy from the central JSON document at construction (raising if it is invalid, so the
    service does not start) and re-reads it when the file changes, checked at most every
    `reload_seconds`. A broken edit is logged and the last valid policy stays in force.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        service: str,
        reload_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._path = Path(path)
        self._service = service
        self._reload_seconds = reload_seconds
        self._clock = clock
        self._policy = load_access_policy(self._path, service=service)
        self._mtime = self._stat()
        self._checked_at = clock()

    async def policy(self) -> AccessPolicy:
        now = self._clock()
        if self._reload_seconds > 0 and now - self._checked_at >= self._reload_seconds:
            self._checked_at = now
            self._reload_if_changed()
        return self._policy

    def cached(self) -> AccessPolicy:
        return self._policy

    def _stat(self) -> float | None:
        try:
            return self._path.stat().st_mtime
        except OSError:
            return None

    def _reload_if_changed(self) -> None:
        mtime = self._stat()
        if mtime == self._mtime:
            return
        try:
            self._policy = load_access_policy(self._path, service=self._service)
        except AccessConfigError as e:
            logger.error("access_config_reload_failed", path=str(self._path), error=str(e))
            return
        self._mtime = mtime
        logger.info("access_config_reloaded", path=str(self._path))
