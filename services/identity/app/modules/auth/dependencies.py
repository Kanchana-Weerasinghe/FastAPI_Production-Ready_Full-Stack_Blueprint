"""
Authentication and authorization dependencies (part of the auth module's public API).

Other modules protect their routes with `CurrentUserDep` and `check_ownership(...)`, so all
access-control decisions live in this one place.
"""

from collections.abc import Callable
from typing import Annotated, Any, Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request

from app.core.errors import AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError
from app.core.security import JWTCookieAuth
from app.modules.auth.permissions import has_permission
from app.modules.users.public import UserAccount, UserUseCases


class ResourceLookup(Protocol):
    async def get_list(self, schema: dict[str, Any]) -> dict[str, Any]: ...


@inject
async def get_current_user(
    claims: dict[str, Any] = Depends(JWTCookieAuth()),
    users: UserUseCases = Depends(Provide["users.use_cases"]),
) -> UserAccount:
    """
    Resolves the authenticated user from the access token cookie.

    Rejects tokens whose `ver` no longer matches the user's `token_version` (password changed,
    signed out everywhere) so revocation takes effect immediately, not when the token expires.
    """
    try:
        user_id = UUID(claims["sub"])
    except (KeyError, ValueError) as e:
        raise AuthenticationError(detail="Invalid token", code="invalid_token") from e
    try:
        user = await users.get_by_id(user_id)
    except NotFoundError as e:
        raise AuthenticationError(detail="User not found", code="invalid_token") from e
    if claims.get("ver") != user.token_version:
        raise AuthenticationError(detail="Session has been revoked", code="token_revoked")
    return user


CurrentUserDep = Annotated[UserAccount, Depends(get_current_user)]


def require_permission(permission: str) -> Any:
    """
    Route dependency enforcing RBAC, e.g. `dependencies=[require_permission(Permission.USERS_READ_ALL)]`.

    Returns 403 `forbidden` when the user's role lacks the permission.
    """

    async def checker(current_user: CurrentUserDep) -> UserAccount:
        if not has_permission(current_user.role, permission):
            raise PermissionDeniedError(detail="You do not have permission to perform this action", code="forbidden")
        return current_user

    return Depends(checker)


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
