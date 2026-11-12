"""
Test support for the access check. Services build their `grant_access` / `deny_access` fixtures on
these: they replace the policy source (the lookup), never the check, so the real `require_access`
runs in every test.

    @pytest.fixture
    def grant_access(app):
        with override_access(app) as access:
            yield access.grant          # grant_access("listUsers", ...)
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI

from platform_kit.access.check import get_access_lookup
from platform_kit.access.lookup import AccessLookup, StaticAccessLookup
from platform_kit.access.policy import ANONYMOUS_ROLE, AccessPolicy


def granting(*operation_ids: str, service: str = "test", public: Iterable[str] = ()) -> StaticAccessLookup:
    """Any signed-in caller may call exactly `operation_ids`; anyone may call `public`."""
    return StaticAccessLookup(
        AccessPolicy(
            service=service,
            role_operations={ANONYMOUS_ROLE: frozenset(public)},
            any_authenticated=frozenset(operation_ids),
        )
    )


def denying(*, service: str = "test", public: Iterable[str] = ()) -> StaticAccessLookup:
    """A signed-in caller may call nothing (beyond `public`)."""
    return granting(service=service, public=public)


@dataclass
class AccessOverride:
    """Handle returned by `override_access`: switch what the test caller may call."""

    app: FastAPI
    service: str = "test"
    public: frozenset[str] = field(default_factory=frozenset)

    def use(self, lookup: AccessLookup) -> None:
        self.app.dependency_overrides[get_access_lookup] = lambda: lookup

    def grant(self, *operation_ids: str) -> None:
        self.use(granting(*operation_ids, service=self.service, public=self.public))

    def deny(self) -> None:
        self.use(denying(service=self.service, public=self.public))


@contextmanager
def override_access(app: FastAPI, *, service: str = "test", public: Iterable[str] = ()) -> Iterator[AccessOverride]:
    """Overrides the lookup for the duration of the block and restores the previous one afterwards."""
    missing = object()
    previous = app.dependency_overrides.get(get_access_lookup, missing)
    try:
        yield AccessOverride(app=app, service=service, public=frozenset(public))
    finally:
        if previous is missing:
            app.dependency_overrides.pop(get_access_lookup, None)
        else:
            app.dependency_overrides[get_access_lookup] = previous  # type: ignore[assignment]
