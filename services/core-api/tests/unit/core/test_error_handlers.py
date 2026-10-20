import json
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException

from app.core.error_handlers import (
    PROBLEM_JSON,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from app.core.errors import ConflictError, NotFoundError


def _request(path: str = "/v2/todos/1") -> MagicMock:
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = path
    request.state.request_id = "req-123"
    return request


def _body(response: Any) -> dict[str, Any]:
    assert response.media_type == PROBLEM_JSON
    body: dict[str, Any] = json.loads(bytes(response.body))
    return body


async def test_app_error_handler_problem_details() -> None:
    """Test that a domain error is rendered as RFC 9457 Problem Details with its stable code and request id."""
    response = await app_error_handler(_request(), NotFoundError("Todo not found", code="todo_not_found"))
    body = _body(response)
    assert response.status_code == 404
    assert body == {
        "type": "https://errors.example.com/todo_not_found",
        "title": "Not Found",
        "status": 404,
        "detail": "Todo not found",
        "instance": "/v2/todos/1",
        "code": "todo_not_found",
        "request_id": "req-123",
    }


async def test_app_error_handler_extension_members() -> None:
    """Test that `extra` members of a domain error are included in the problem body."""
    response = await app_error_handler(_request(), ConflictError("Version mismatch", extra={"current_version": 3}))
    body = _body(response)
    assert body["status"] == 409
    assert body["code"] == "conflict"
    assert body["current_version"] == 3


async def test_http_exception_handler_maps_framework_errors() -> None:
    """Test that framework HTTP errors (e.g. unknown routes) also use the problem format."""
    response = await http_exception_handler(_request("/nope"), HTTPException(status_code=404, detail="Not Found"))
    body = _body(response)
    assert body["code"] == "not_found"
    assert body["instance"] == "/nope"


async def test_validation_exception_handler_lists_fields() -> None:
    """Test that validation errors return 422 with one entry per invalid field."""
    exc = RequestValidationError([{"loc": ("body", "title"), "msg": "field required", "type": "missing"}])
    body = _body(await validation_exception_handler(_request(), exc))
    assert body["status"] == 422
    assert body["code"] == "validation_failed"
    assert body["errors"] == [{"field": "title", "message": "Field required", "type": "missing"}]


async def test_rate_limit_exception_handler() -> None:
    """Test that rate limiting returns 429 with the rate_limited code."""
    body = _body(await rate_limit_exception_handler(_request(), MagicMock(spec=RateLimitExceeded)))
    assert body["status"] == 429
    assert body["code"] == "rate_limited"


async def test_generic_exception_handler() -> None:
    """Test that unexpected errors return a generic 500 without internal details and are logged."""
    with patch("app.core.error_handlers.logger") as mock_logger:
        response = await generic_exception_handler(_request("/api/v2/todos"), Exception("db password is hunter2"))
    body = _body(response)
    assert response.status_code == 500
    assert body["code"] == "internal_error"
    assert "hunter2" not in json.dumps(body)
    mock_logger.exception.assert_called_once()
