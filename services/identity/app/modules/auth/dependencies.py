"""
Authentication and access dependencies (part of the auth module's public API).

- `get_access_subject`: who is calling, for the central access check (`platform_kit.access.require_access`,
  applied on every router). What each role may call is data in `config/access-control.json`, never code.
- `CurrentUserDep`: the signed-in user, for routes that act on the caller's own account.
- `check_ownership(...)`: row-level rule "only the owner may touch this resource" (a business rule,
  not access control).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request
from platform_kit.access import AccessSubject

from app.core.config import config
from app.core.errors import AppError, AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError
from app.core.security import decode_token
from app.modules.users.public import UserAccount, UserUseCases


class ResourceLookup(Protocol):
    async def get_list(self, schema: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class Session:
    """The caller's session as resolved from the access token cookie: a user, or why there is none."""

    user: UserAccount | None
    error: AppError | None = None


@inject
async def resolve_session(
    request: Request,
    users: UserUseCases = Depends(Provide["users.use_cases"]),
) -> Session:
    """
    Resolves the access token cookie once per request (FastAPI caches it for every dependency).

    Never raises for missing or invalid credentials, so public endpoints keep working; the error is kept
    and raised by `get_current_user` or by the access check when the endpoint is not public. Rejects
    tokens whose `ver` no longer matches the user's `token_version` (password changed, signed out
    everywhere), so revocation takes effect immediately, not when the token expires.
    """
    token = request.cookies.get(config.AUTH_COOKIE_NAME)
    if not token:
        return Session(None, AuthenticationError("Not authenticated", code="not_authenticated"))
    try:
        claims = decode_token(token, "access")
        user_id = UUID(claims["sub"])
    except AuthenticationError as e:
        return Session(None, e)
    except (KeyError, ValueError):
        return Session(None, AuthenticationError(detail="Invalid token", code="invalid_token"))
    try:
        user = await users.get_by_id(user_id)
    except NotFoundError:
        return Session(None, AuthenticationError(detail="User not found", code="invalid_token"))
    if claims.get("ver") != user.token_version:
        return Session(None, AuthenticationError(detail="Session has been revoked", code="token_revoked"))
    return Session(user)


SessionDep = Annotated[Session, Depends(resolve_session)]


async def get_current_user(session: SessionDep) -> UserAccount:
    """The authenticated user (401 otherwise)."""
    if session.user is None:
        raise session.error or AuthenticationError("Not authenticated", code="not_authenticated")
    return session.user


CurrentUserDep = Annotated[UserAccount, Depends(get_current_user)]


def roles_of(user: UserAccount) -> frozenset[str]:
    """
    The roles a signed-in user holds, as named in the access document. The single place that maps a
    principal to roles: today the account's role; with Azure AD, the token's groups / object id.
    """
    return frozenset({str(user.role)})


async def get_access_subject(session: SessionDep) -> AccessSubject:
    """The caller as the access check sees it: signed in with roles, or anonymous (with the reason)."""
    if session.user is None:
        return AccessSubject.anonymous(session.error)
    return AccessSubject.signed_in(roles_of(session.user))


def check_ownership(
    service_id: str,
    param_name: str = "id",
    is_active: bool | None = True,
) -> Callable[..., Any]:
    """
    Dependency factory to verify resource existence and ownership.

    Args:
        service_id: Container path of the resource's service, e.g. "projects.use_cases".
        param_name: The name of the path parameter containing the resource ID.
        is_active: Filter by active status (True, False, or None for any).

    Returns:
        An async validation function that returns the resource if the current user owns it.
    """

    @inject
    async def validation(
        request: Request,
        current_user: UserAccount = Depends(get_current_user),
        service: ResourceLookup = Depends(Provide[service_id]),
    ) -> Any:
        obj_id = request.path_params.get(param_name)
        if not obj_id:
            raise NotFoundError(detail=f"{param_name} not found in path")
        try:
            uid = UUID(obj_id)
        except (ValueError, AttributeError) as err:
            raise BadRequestError(detail="Invalid resource ID format") from err
        results = await service.get_list({"id__eq": uid, "is_active": is_active})
        resource = results["founds"][0] if results["founds"] else None
        if not resource:
            raise NotFoundError(detail="Resource not found")
        if getattr(resource, "user_id", None) != current_user.id:
            raise PermissionDeniedError(detail="Not authorized to access this resource")
        return resource

    return validation
