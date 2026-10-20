import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from platform_kit.errors import NotFoundError, PreconditionFailedError
from platform_kit.http.conditional import check_if_match, etag_for
from platform_kit.http.problems import PROBLEM_JSON, exception_handlers
from platform_kit.logging import REDACTED, redact_sensitive


def _app() -> FastAPI:
    app = FastAPI()
    for exc_type, handler in exception_handlers("https://errors.test").items():
        app.add_exception_handler(exc_type, handler)

    class Body(BaseModel):
        name: str

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Thing not found")

    @app.post("/things")
    async def create(body: Body) -> Body:
        return body

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    return app


def test_app_error_becomes_problem_details() -> None:
    response = TestClient(_app()).get("/missing")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    body = response.json()
    assert body["type"] == "https://errors.test/not_found"
    assert body["detail"] == "Thing not found"
    assert body["instance"] == "/missing"


def test_validation_error_lists_fields() -> None:
    response = TestClient(_app()).post("/things", json={})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "name"


def test_unexpected_error_hides_internals() -> None:
    response = TestClient(_app(), raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    assert "secret internals" not in response.text


def test_unknown_route_is_problem_details() -> None:
    response = TestClient(_app()).get("/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.parametrize("header", [None, 'W/"3"', '"3"', "*", 'W/"1", W/"3"'])
def test_check_if_match_accepts_current_version(header: str | None) -> None:
    check_if_match(header, 3)


def test_check_if_match_rejects_stale_version() -> None:
    with pytest.raises(PreconditionFailedError) as excinfo:
        check_if_match('W/"2"', 3)
    assert excinfo.value.extra == {"current_etag": etag_for(3)}


def test_logs_redact_secrets_and_emails() -> None:
    event = redact_sensitive(None, "info", {"event": "x", "authorization": "Bearer t", "note": "mail a@b.com"})
    assert event["authorization"] == REDACTED
    assert event["note"] == "mail [EMAIL]"
