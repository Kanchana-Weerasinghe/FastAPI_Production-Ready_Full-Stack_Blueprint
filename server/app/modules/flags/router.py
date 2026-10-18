from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path

from app.core.security import rate_limit
from app.modules.auth.dependencies import CurrentUserDep, require_permission
from app.modules.auth.permissions import Permission
from app.modules.flags.domain.entities import FeatureFlagState
from app.modules.flags.schemas import EvaluatedFlags, FeatureFlag, FeatureFlagUpdate
from app.modules.flags.service import FeatureFlagService

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])

FlagServiceDep = Annotated[FeatureFlagService, Depends(Provide["flags.service"])]


@router.get("/me", response_model=EvaluatedFlags, summary="My Feature Flags", dependencies=[rate_limit("120/minute")])
@inject
async def my_flags(current_user: CurrentUserDep, service: FlagServiceDep) -> EvaluatedFlags:
    """Flags evaluated for the current user; the web app uses this to show or hide features."""
    return EvaluatedFlags(flags=await service.evaluate_all(current_user, current_user.role))


@router.get(
    "/",
    response_model=list[FeatureFlag],
    summary="List Feature Flags (admin)",
    dependencies=[rate_limit("60/minute"), require_permission(Permission.FLAGS_MANAGE)],
)
@inject
async def list_flags(service: FlagServiceDep) -> list[FeatureFlagState]:
    """All flags with their configuration. Requires `flags:manage`."""
    return await service.list_all()


@router.put(
    "/{key}",
    response_model=FeatureFlag,
    summary="Create or Update Feature Flag (admin)",
    dependencies=[rate_limit("30/minute"), require_permission(Permission.FLAGS_MANAGE)],
)
@inject
async def upsert_flag(
    data: FeatureFlagUpdate,
    current_user: CurrentUserDep,
    service: FlagServiceDep,
    key: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_.-]{1,99}$")],
) -> FeatureFlagState:
    """Creates or changes a flag (audited). Requires `flags:manage`."""
    return await service.upsert(key, data.model_dump(), current_user)
