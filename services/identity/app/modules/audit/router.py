from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.core.security import rate_limit
from app.modules.audit.public import AuditService
from app.modules.audit.schemas import AuditLogPage, FindAuditLog
from app.modules.auth.dependencies import require_permission
from app.modules.auth.permissions import Permission

router = APIRouter(prefix="/audit-logs", tags=["audit"])

AuditServiceDep = Annotated[AuditService, Depends(Provide["audit.service"])]


@router.get(
    "/",
    response_model=AuditLogPage,
    summary="List Audit Logs (admin)",
    dependencies=[rate_limit("60/minute"), require_permission(Permission.AUDIT_READ)],
)
@inject
async def list_audit_logs(query: Annotated[FindAuditLog, Query()], service: AuditServiceDep) -> Any:
    """Searches the audit trail, newest first. Requires the `audit:read` permission."""
    filters = query.model_dump(exclude_none=True, exclude={"cursor", "limit"})
    return await service.feed(filters, cursor=query.cursor, limit=query.limit)
