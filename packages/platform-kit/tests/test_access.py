import json
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI, Header
from fastapi.testclient import TestClient

from platform_kit.access import (
    ANONYMOUS_ROLE,
    AccessConfigError,
    AccessGrant,
    AccessLookup,
    AccessPolicy,
    AccessSubject,
    JsonFileAccessLookup,
    StaticAccessLookup,
    access_setup_errors,
    check_access,
    install_access,
    load_access_policy,
    require_access,
)
from platform_kit.access.testing import override_access
from platform_kit.errors import AuthenticationError
from platform_kit.http.problems import exception_handlers

REPO_ACCESS_DOCUMENT = Path(__file__).resolve().parents[3] / "config" / "access-control.json"


async def _subject(x_test_roles: Annotated[str | None, Header()] = None) -> AccessSubject:
    """Test resolver: header absent = anonymous, `invalid` = rejected credentials, else comma-separated roles."""
    if x_test_roles is None:
        return AccessSubject.anonymous()
    if x_test_roles == "invalid":
        return AccessSubject.anonymous(AuthenticationError("Access token expired", code="token_expired"))
    return AccessSubject.signed_in(x_test_roles.split(","))


def _policy() -> AccessPolicy:
    return AccessPolicy(
        service="things",
        role_operations={
            ANONYMOUS_ROLE: frozenset({"readPublic"}),
            "reader": frozenset({"listThings"}),
            "editor": frozenset({"listThings", "deleteThing", "editAnyThing"}),
        },
    )


def _app(lookup: AccessLookup | None = None, *, install: bool = True) -> FastAPI:
    app = FastAPI()
    for exc_type, handler in exception_handlers("https://errors.test").items():
        app.add_exception_handler(exc_type, handler)
    router = APIRouter(prefix="/things", dependencies=[require_access()])

    @router.get("/public", operation_id="readPublic")
    async def read_public() -> dict[str, str]:
        return {"ok": "public"}

    @router.get("/", operation_id="listThings")
    async def list_things() -> dict[str, str]:
        return {"ok": "list"}

    @router.delete("/{thing_id}", operation_id="deleteThing")
    async def delete_thing(thing_id: str, grant: Annotated[AccessGrant, Depends(check_access)]) -> dict[str, bool]:
        return {"editAny": grant.allows("editAnyThing"), "id": thing_id == "1"}

    @router.post("/new", operation_id="createThing")  # granted to nobody
    async def create_thing() -> dict[str, str]:
        return {"ok": "created"}

    app.include_router(router)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    if install:
        install_access(
            app, subject=_subject, lookup=lookup or StaticAccessLookup(_policy()), extra_operations={"editAnyThing"}
        )
    return app


# --- The check ---------------------------------------------------------------------------------


def test_granted_role_passes() -> None:
    response = TestClient(_app()).get("/things/", headers={"x-test-roles": "reader"})
    assert response.status_code == 200


def test_role_without_the_privilege_gets_403_access_denied() -> None:
    response = TestClient(_app()).delete("/things/1", headers={"x-test-roles": "reader"})
    assert response.status_code == 403
    assert response.json()["code"] == "access_denied"


def test_unmapped_endpoint_is_denied_even_to_the_most_privileged_role() -> None:
    response = TestClient(_app()).post("/things/new", headers={"x-test-roles": "editor,reader"})
    assert response.status_code == 403
    assert response.json()["code"] == "access_denied"


def test_unknown_role_gets_nothing() -> None:
    assert TestClient(_app()).get("/things/", headers={"x-test-roles": "stranger"}).status_code == 403


def test_no_credentials_on_a_protected_endpoint_is_401() -> None:
    response = TestClient(_app()).get("/things/")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_rejected_credentials_keep_their_401_code() -> None:
    response = TestClient(_app()).get("/things/", headers={"x-test-roles": "invalid"})
    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


def test_public_endpoint_is_open_to_anonymous_and_signed_in_callers() -> None:
    client = TestClient(_app())
    assert client.get("/things/public").status_code == 200
    assert client.get("/things/public", headers={"x-test-roles": "invalid"}).status_code == 200
    assert client.get("/things/public", headers={"x-test-roles": "reader"}).status_code == 200


def test_grant_lists_every_operation_of_the_caller() -> None:
    client = TestClient(_app())
    assert client.delete("/things/1", headers={"x-test-roles": "editor"}).json() == {"editAny": True, "id": True}


class _BrokenLookup(StaticAccessLookup):
    async def policy(self) -> AccessPolicy:
        raise ConnectionError("store unreachable")


def test_unreachable_store_denies() -> None:
    client = TestClient(_app(_BrokenLookup(_policy())))
    assert client.get("/things/", headers={"x-test-roles": "editor"}).status_code == 403
    assert client.get("/things/public").status_code == 401


def test_check_without_install_fails_closed() -> None:
    client = TestClient(_app(install=False), raise_server_exceptions=False)
    assert client.get("/things/public").status_code == 500


# --- Test overrides ----------------------------------------------------------------------------


def test_override_grants_exactly_the_given_operations_and_restores_afterwards() -> None:
    app = _app()
    client = TestClient(app)
    with override_access(app) as access:
        access.grant("deleteThing")
        assert client.delete("/things/1", headers={"x-test-roles": "reader"}).status_code == 200
        assert client.get("/things/", headers={"x-test-roles": "editor"}).status_code == 403
        assert client.delete("/things/1").status_code == 401  # still needs a signed-in caller
        access.deny()
        assert client.delete("/things/1", headers={"x-test-roles": "editor"}).status_code == 403
    assert client.get("/things/", headers={"x-test-roles": "reader"}).status_code == 200


# --- Setup validation --------------------------------------------------------------------------


def test_setup_errors_report_missing_operation_id_missing_check_duplicates_and_unknown_grants() -> None:
    app = FastAPI()
    unchecked = APIRouter()
    checked = APIRouter(dependencies=[require_access()])

    @unchecked.get("/open", operation_id="openThing")
    async def open_thing() -> None: ...

    @checked.get("/anonymous")
    async def no_operation_id() -> None: ...

    @checked.get("/a", operation_id="sameName")
    async def first() -> None: ...

    @checked.get("/b", operation_id="sameName")
    async def second() -> None: ...

    app.include_router(unchecked)
    app.include_router(checked)
    policy = AccessPolicy(service="things", role_operations={"r": frozenset({"sameName", "ghost"})})

    errors = access_setup_errors(app, policy=policy)

    assert any("/open: router does not apply require_access()" in e for e in errors)
    assert any("/anonymous: missing operation_id" in e for e in errors)
    assert any("'sameName' also used by" in e for e in errors)
    assert any("unknown operation 'ghost'" in e for e in errors)


def test_install_refuses_an_invalid_setup() -> None:
    app = FastAPI()

    @app.get("/open", operation_id="openThing")
    async def open_thing() -> None: ...

    with pytest.raises(RuntimeError, match="require_access"):
        install_access(app, subject=_subject, lookup=StaticAccessLookup(_policy()))


def test_health_routes_are_exempt() -> None:
    assert access_setup_errors(_app(), policy=_policy(), extra_operations={"editAnyThing"}) == []


# --- The central JSON document -----------------------------------------------------------------


def _document(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


DOCUMENT = {
    "privileges": {
        "read": {"name": "Read", "endpoints": {"things": ["listThings"], "other": ["otherOp"]}},
        "public": {"name": "Public", "endpoints": {"things": ["readPublic"]}},
    },
    "roles": {"anonymous": ["public"], "reader": ["read"]},
}


def test_document_keeps_only_this_services_operations(tmp_path: Path) -> None:
    policy = load_access_policy(_document(tmp_path / "a.json", DOCUMENT), service="things")
    assert policy.role_operations == {"anonymous": frozenset({"readPublic"}), "reader": frozenset({"listThings"})}


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        json.dumps({"privileges": {}, "roles": {"reader": ["missing"]}}),
        json.dumps({"privileges": {"p": {"name": "", "endpoints": {}}}, "roles": {}}),
        json.dumps({**DOCUMENT, "unexpected": 1}),
    ],
)
def test_invalid_document_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AccessConfigError):
        load_access_policy(path, service="things")


def test_missing_document_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AccessConfigError):
        JsonFileAccessLookup(tmp_path / "absent.json", service="things")


async def test_file_lookup_reloads_changes_and_keeps_last_good_policy(tmp_path: Path) -> None:
    now = [0.0]
    path = _document(tmp_path / "a.json", DOCUMENT)
    lookup = JsonFileAccessLookup(path, service="things", reload_seconds=10, clock=lambda: now[0])
    changed = {**DOCUMENT, "roles": {"reader": ["read", "public"]}}

    _document(path, changed)
    import os

    os.utime(path, (1, 1))  # make the change visible even on coarse-mtime filesystems
    assert (await lookup.policy()).role_operations["reader"] == frozenset({"listThings"})  # not yet re-checked
    now[0] = 10
    assert (await lookup.policy()).role_operations["reader"] == frozenset({"listThings", "readPublic"})

    path.write_text("{broken", encoding="utf-8")
    os.utime(path, (2, 2))
    now[0] = 20
    assert (await lookup.policy()).role_operations["reader"] == frozenset({"listThings", "readPublic"})


def test_repository_access_document_is_valid() -> None:
    assert load_access_policy(REPO_ACCESS_DOCUMENT, service="identity").operations
