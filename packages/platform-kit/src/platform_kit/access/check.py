"""
The one access check every service applies: `APIRouter(..., dependencies=[require_access()])`.

For each request it reads the matched route's `operation_id`, asks the service's `AccessLookup` for
the policy, and lets the call through only if a role of the caller (or the implicit `anonymous`
role) holds it. Everything else is refused (deny by default):

- endpoint not granted and the caller is not signed in -> 401 (the credential error, if any);
- endpoint not granted to a signed-in caller             -> 403 `access_denied`;
- policy unavailable                                     -> treated as "nothing granted".

Ownership ("only the owner may ...") is a business rule and stays in the use cases.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.routing import APIRoute

from platform_kit.access.lookup import AccessLookup
from platform_kit.access.policy import AccessPolicy, AccessSubject
from platform_kit.errors import AccessDeniedError, AuthenticationError
from platform_kit.logging import logger

DEFAULT_EXEMPT_PATH_PREFIXES = ("/health",)


@dataclass(frozen=True, slots=True)
class AccessGrant:
    """Result of a passed check: the operation called and everything the caller may call."""

    operation_id: str
    operations: frozenset[str]
    subject: AccessSubject

    def allows(self, operation_id: str) -> bool:
        return operation_id in self.operations


async def get_access_subject() -> AccessSubject:
    """Placeholder; each service plugs in its own resolver with `install_access(...)`."""
    raise RuntimeError("Access control is not installed: call platform_kit.access.install_access(app, ...)")


async def get_access_lookup(request: Request) -> AccessLookup:
    """The service's policy source. Tests override this dependency (`grant_access` / `deny_access`)."""
    lookup: AccessLookup | None = getattr(request.app.state, "access_lookup", None)
    if lookup is None:
        raise RuntimeError("Access control is not installed: call platform_kit.access.install_access(app, ...)")
    return lookup


async def _current_policy(lookup: AccessLookup) -> AccessPolicy | None:
    try:
        return await lookup.policy()
    except Exception as e:  # fail closed: an unavailable store grants nothing
        logger.error("access_lookup_failed", error=str(e))
        return None


async def check_access(
    request: Request,
    subject: AccessSubject = Depends(get_access_subject),
    lookup: AccessLookup = Depends(get_access_lookup),
) -> AccessGrant:
    route = request.scope.get("route")
    operation_id: str | None = getattr(route, "operation_id", None)
    policy = await _current_policy(lookup)
    operations = policy.operations_for(subject) if policy else frozenset()
    if operation_id and operation_id in operations:
        return AccessGrant(operation_id=operation_id, operations=operations, subject=subject)
    if not subject.authenticated:
        if subject.authentication_error is not None:
            raise subject.authentication_error
        raise AuthenticationError("Authentication required")
    logger.warning("access_denied", operation_id=operation_id, roles=sorted(subject.roles))
    raise AccessDeniedError("You do not have access to this operation")


def require_access() -> Any:
    """The router-level dependency: `APIRouter(..., dependencies=[require_access()])`."""
    return Depends(check_access)


# --- Wiring and validation -----------------------------------------------------------------------


def _api_routes(app: FastAPI) -> list[Any]:
    """
    Every endpoint as mounted, with its effective path, methods, operation_id and dependencies.
    FastAPI >= 0.150 keeps included routers nested (`iter_route_contexts` flattens them); older
    versions copy the routes into `app.routes`.
    """
    try:
        from fastapi.routing import iter_route_contexts  # type: ignore[attr-defined,unused-ignore]
    except ImportError:
        return [route for route in app.routes if isinstance(route, APIRoute)]
    return [ctx for ctx in iter_route_contexts(app.routes) if isinstance(ctx.original_route, APIRoute)]


def _uses_check(route: Any) -> bool:
    pending = list(route.dependant.dependencies)
    while pending:
        dependant = pending.pop()
        if dependant.call is check_access:
            return True
        pending.extend(dependant.dependencies)
    return False


def access_setup_errors(
    app: FastAPI,
    *,
    policy: AccessPolicy | None = None,
    extra_operations: Iterable[str] = (),
    exempt_path_prefixes: Iterable[str] = DEFAULT_EXEMPT_PATH_PREFIXES,
) -> list[str]:
    """
    Problems that would leave an endpoint unchecked or mis-mapped (empty list = OK):
    a route without `operation_id`, a route without `require_access()`, a duplicated `operation_id`,
    or a policy entry naming an operation the service does not have.
    """
    exempt = tuple(exempt_path_prefixes)
    errors: list[str] = []
    seen: dict[str, str] = {}
    for route in _api_routes(app):
        path: str = route.path
        if path.startswith(exempt):
            continue
        label = f"{','.join(sorted(route.methods or ()))} {path}"
        if not route.operation_id:
            errors.append(f"{label}: missing operation_id")
        elif route.operation_id in seen:
            errors.append(f"{label}: operation_id {route.operation_id!r} also used by {seen[route.operation_id]}")
        else:
            seen[route.operation_id] = label
        if not _uses_check(route):
            errors.append(f"{label}: router does not apply require_access()")
    if policy is not None:
        known = set(seen) | set(extra_operations)
        for operation in sorted(policy.operations - known):
            errors.append(f"access policy grants unknown operation {operation!r} in service {policy.service!r}")
    return errors


def route_operation_ids(
    app: FastAPI, *, exempt_path_prefixes: Iterable[str] = DEFAULT_EXEMPT_PATH_PREFIXES
) -> frozenset[str]:
    """The operation_ids of every access-controlled route (e.g. to find routes no role is granted)."""
    exempt = tuple(exempt_path_prefixes)
    return frozenset(
        route.operation_id for route in _api_routes(app) if route.operation_id and not route.path.startswith(exempt)
    )


def install_access(
    app: FastAPI,
    *,
    subject: Callable[..., Any],
    lookup: AccessLookup,
    extra_operations: Iterable[str] = (),
    exempt_path_prefixes: Iterable[str] = DEFAULT_EXEMPT_PATH_PREFIXES,
) -> None:
    """
    Plugs the service's caller resolver and policy source into `require_access()` and validates the
    setup. Call it after the routers are mounted; it raises (the service does not start) on any error.

    `subject` is a FastAPI dependency returning an `AccessSubject`. It must not raise for missing or
    invalid credentials: return `AccessSubject.anonymous(error)` so public endpoints keep working.
    `extra_operations` are operations checked inside use cases (`AccessGrant.allows`) rather than routes.
    """
    app.dependency_overrides[get_access_subject] = subject
    app.state.access_lookup = lookup
    errors = access_setup_errors(
        app, policy=lookup.cached(), extra_operations=extra_operations, exempt_path_prefixes=exempt_path_prefixes
    )
    if errors:
        raise RuntimeError("Access control setup is invalid:\n  " + "\n  ".join(errors))


__all__ = [
    "AccessGrant",
    "access_setup_errors",
    "check_access",
    "get_access_lookup",
    "get_access_subject",
    "install_access",
    "require_access",
    "route_operation_ids",
]
