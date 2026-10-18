from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import AsyncMock

import pytest
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import Message, Receive, Scope, Send

from app.core.database import Database
from app.shared.idempotency import IdempotencyMiddleware


async def _unused_app(_scope: Scope, _receive: Receive, _send: Send) -> None:
    raise AssertionError("The middleware app is not used by this test")


async def test_idempotent_response_preserves_background_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify idempotency response buffering retains post-commit response work."""
    middleware = IdempotencyMiddleware(_unused_app, cast(Database, object()))
    monkeypatch.setattr(middleware, "_claim", AsyncMock(return_value=None))
    monkeypatch.setattr(middleware, "_complete", AsyncMock())
    callbacks: list[str] = []
    background = BackgroundTask(lambda: callbacks.append("completed"))

    async def receive() -> Message:
        return {"type": "http.request", "body": b"payload", "more_body": False}

    scope: Scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/widgets",
        "raw_path": b"/widgets",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), (b"idempotency-key", b"request-key")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    request = Request(scope, receive)

    async def body() -> AsyncIterator[bytes]:
        yield b"result"

    async def call_next(_: Request) -> Response:
        return StreamingResponse(body(), background=background)

    response = await middleware.dispatch(request, call_next)

    assert response.body == b"result"
    assert response.background is background
    await response.background()
    assert callbacks == ["completed"]
