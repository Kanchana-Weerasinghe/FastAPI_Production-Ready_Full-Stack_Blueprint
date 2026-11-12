from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response, status
from platform_kit.access import require_access

from app.core.security import clear_auth_cookies, rate_limit
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.users.domain.entities import UserAccount
from app.modules.users.public import UserUseCases
from app.modules.users.schemas import User, UserAdminView
from app.shared.schemas import BaseListResponse, PaginationMixin

router = APIRouter(prefix="/user", tags=["users"], dependencies=[require_access()])
admin_router = APIRouter(prefix="/users", tags=["users"], dependencies=[require_access()])

UserUseCasesDep = Annotated[UserUseCases, Depends(Provide["users.use_cases"])]


@router.get(
    "/me",
    response_model=User,
    summary="Get Current User",
    operation_id="getCurrentUser",
    dependencies=[rate_limit("200/minute")],
)
async def get_me(current_user: CurrentUserDep) -> UserAccount:
    """Returns the profile information of the currently authenticated user."""
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Current User",
    operation_id="deleteCurrentUser",
    dependencies=[rate_limit("5/minute")],
)
@inject
async def delete_me(response: Response, current_user: CurrentUserDep, users: UserUseCasesDep) -> None:
    """Deletes the current user's account, clears the session and, after commit, removes their files."""
    await users.delete_account(current_user)
    clear_auth_cookies(response)


@admin_router.get(
    "/",
    response_model=BaseListResponse[UserAdminView],
    summary="List Users (admin)",
    operation_id="listUsers",
    dependencies=[rate_limit("60/minute")],
)
@inject
async def list_users(query: Annotated[PaginationMixin, Query()], users: UserUseCasesDep) -> Any:
    """Lists all user accounts. Granted through the access document (`listUsers`)."""
    return await users.get_list(query.model_dump(exclude_none=True))
