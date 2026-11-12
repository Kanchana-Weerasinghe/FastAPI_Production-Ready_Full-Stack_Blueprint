from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from platform_kit.access import require_access

from app.core.security import rate_limit
from app.modules.audit.public import AuditService
from app.modules.audit.schemas import AuditLogPage, FindAuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"], dependencies=[require_access()])

AuditServiceDep = Annotated[AuditService, Depends(Provide["audit.service"])]


@router.get(
    "/",
    response_model=AuditLogPage,
    summary="List Audit Logs (admin)",
    operation_id="listAuditLogs",
    dependencies=[rate_limit("60/minute")],
)
@inject
async def list_audit_logs(query: Annotated[FindAuditLog, Query()], service: AuditServiceDep) -> Any:
    """Searches the audit trail, newest first. Granted through the access document (`listAuditLogs`)."""
    filters = query.model_dump(exclude_none=True, exclude={"cursor", "limit"})
    return await service.feed(filters, cursor=query.cursor, limit=query.limit)
