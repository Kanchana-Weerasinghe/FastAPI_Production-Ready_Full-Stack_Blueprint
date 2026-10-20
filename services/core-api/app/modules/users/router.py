from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import clear_auth_cookies, rate_limit
from app.modules.auth.dependencies import CurrentUserDep, require_permission
from app.modules.auth.permissions import Permission
from app.modules.users.domain.entities import UserAccount
from app.modules.users.schemas import User, UserAdminView
from app.modules.users.service import UserService
from app.shared.schemas import BaseListResponse, PaginationMixin

router = APIRouter(prefix="/user", tags=["users"])
admin_router = APIRouter(prefix="/users", tags=["users"])

UserServiceDep = Annotated[UserService, Depends(Provide["users.service"])]


@router.get("/me", response_model=User, summary="Get Current User", dependencies=[rate_limit("200/minute")])
async def get_me(current_user: CurrentUserDep) -> UserAccount:
    """Returns the profile information of the currently authenticated user."""
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Current User",
    dependencies=[rate_limit("5/minute")],
)
@inject
async def delete_me(response: Response, current_user: CurrentUserDep, service: UserServiceDep) -> None:
    """Deletes the current user's account, clears the session and, after commit, removes their files."""
    await service.delete_account(current_user)
    clear_auth_cookies(response)


@admin_router.get(
    "/",
    response_model=BaseListResponse[UserAdminView],
    summary="List Users (admin)",
    dependencies=[rate_limit("60/minute"), require_permission(Permission.USERS_READ_ALL)],
)
@inject
async def list_users(query: Annotated[PaginationMixin, Query()], service: UserServiceDep) -> Any:
    """Lists all user accounts. Requires the `users:read_all` permission (admin role)."""
    return await service.get_list(query.model_dump(exclude_none=True))
