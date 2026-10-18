import json
from datetime import UTC, datetime
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.security import rate_limit
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.privacy.service import PrivacyService

router = APIRouter(prefix="/user", tags=["privacy"])

PrivacyServiceDep = Annotated[PrivacyService, Depends(Provide["privacy.service"])]


@router.get(
    "/me/export",
    summary="Export My Data",
    response_class=Response,
    responses={200: {"content": {"application/json": {}}, "description": "Downloadable JSON export"}},
    dependencies=[rate_limit("3/hour")],
)
@inject
async def export_my_data(current_user: CurrentUserDep, service: PrivacyServiceDep) -> Response:
    """Downloads all personal data stored about the current user as JSON (data portability)."""
    data = await service.export(current_user)
    filename = f"my-data-{datetime.now(UTC):%Y%m%d}.json"
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
