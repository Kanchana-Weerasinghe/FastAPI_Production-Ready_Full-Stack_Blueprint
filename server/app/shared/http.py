"""
Resilient outbound HTTP: timeouts, retries with exponential backoff + jitter, and a circuit breaker.

Every call to a third-party service should go through `ResilientHttpClient` so a slow or failing
dependency degrades one feature instead of exhausting the event loop or connection pool.
"""

import asyncio
import random
import time
from typing import Any

import httpx
import structlog

from app.core.config import config
from app.core.errors import ServiceUnavailableError
from app.core.logging import logger

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class CircuitOpenError(ServiceUnavailableError):
    code = "dependency_unavailable"
    title = "Dependency Unavailable"


class CircuitBreaker:
    """
    Classic three-state breaker (closed → open → half-open), per dependency and per process.

    After `failure_threshold` consecutive failures calls fail fast for `reset_seconds`; then one
    trial call is let through and its outcome closes or re-opens the circuit.
    """

    def __init__(self, name: str, failure_threshold: int, reset_seconds: float) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            return "half_open"
        return "open"

    def before_call(self) -> None:
        if self.state == "open":
            raise CircuitOpenError(f"{self.name} is temporarily unavailable")

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self.state == "half_open" or self._failures >= self.failure_threshold:
            if self._opened_at is None or self.state == "half_open":
                logger.warning("circuit_breaker_opened", dependency=self.name, failures=self._failures)
            self._opened_at = time.monotonic()


def backoff_delay(attempt: int, base: float = 0.2, cap: float = 5.0) -> float:
    """Exponential backoff with full jitter (AWS architecture blog), attempt starting at 1."""
    return random.uniform(0, min(cap, base * 2 ** (attempt - 1)))  # noqa: S311 - jitter, not crypto


class ResilientHttpClient:
    """
    httpx.AsyncClient wrapper for one upstream dependency.

    - Timeouts on every request (`HTTP_TIMEOUT_SECONDS`).
    - Retries connection errors/timeouts and retryable statuses, but only for idempotent methods
      unless `retry_non_idempotent=True` (e.g. the upstream supports idempotency keys).
    - Opens a circuit breaker after repeated failures.
    """

    def __init__(self, name: str, base_url: str = "", headers: dict[str, str] | None = None) -> None:
        self.name = name
        self.client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=config.HTTP_TIMEOUT_SECONDS)
        self.breaker = CircuitBreaker(
            name, config.CIRCUIT_BREAKER_FAILURE_THRESHOLD, config.CIRCUIT_BREAKER_RESET_SECONDS
        )

    async def request(
        self, method: str, url: str, *, retry_non_idempotent: bool = False, **kwargs: Any
    ) -> httpx.Response:
        may_retry = method.upper() in IDEMPOTENT_METHODS or retry_non_idempotent
        attempts = config.HTTP_MAX_RETRIES + 1 if may_retry else 1
        # Propagate the correlation id so upstream logs can be joined with ours.
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        if request_id:
            kwargs["headers"] = {"X-Request-ID": request_id, **(kwargs.get("headers") or {})}
        for attempt in range(1, attempts + 1):
            self.breaker.before_call()
            try:
                response = await self.client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                self.breaker.record_failure()
                logger.warning("http_dependency_error", dependency=self.name, attempt=attempt, error=type(e).__name__)
                if attempt == attempts:
                    raise
            else:
                if response.status_code not in RETRYABLE_STATUS:
                    self.breaker.record_success()
                    return response
                self.breaker.record_failure()
                logger.warning("http_dependency_retryable_status", dependency=self.name, status=response.status_code)
                if attempt == attempts:
                    return response
            await asyncio.sleep(backoff_delay(attempt))
        raise RuntimeError("unreachable")  # pragma: no cover

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def aclose(self) -> None:
        await self.client.aclose()
