from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.core.errors import NotFoundError
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.flags.application.use_cases.service import FeatureFlagService


def require_flag(key: str) -> Any:
    """
    Route dependency hiding an endpoint while its flag is off for the current user, answering 404
    as if the endpoint did not exist: `dependencies=[require_flag("new_editor")]`.
    """

    @inject
    async def checker(
        current_user: CurrentUserDep, service: FeatureFlagService = Depends(Provide["flags.service"])
    ) -> None:
        if not await service.is_enabled(key, current_user, current_user.role):
            raise NotFoundError("Not found")

    return Depends(checker)
