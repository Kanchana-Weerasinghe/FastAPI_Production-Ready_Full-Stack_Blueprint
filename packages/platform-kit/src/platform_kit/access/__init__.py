"""
Central, data-driven access control (see docs/adr/0017-central-access-control.md).

    router = APIRouter(prefix="/things", tags=["things"], dependencies=[require_access()])

    @router.get("/", operation_id="listThings")
    ...

Who may call which `(service, operationId)` is data (the central access document today, the access
tables later), never code. Endpoints no privilege includes are refused.
"""

from platform_kit.access.check import (
    AccessGrant,
    access_setup_errors,
    check_access,
    get_access_lookup,
    get_access_subject,
    install_access,
    require_access,
    route_operation_ids,
)
from platform_kit.access.lookup import AccessLookup, JsonFileAccessLookup, StaticAccessLookup, load_access_policy
from platform_kit.access.policy import (
    ANONYMOUS_ROLE,
    AccessConfigError,
    AccessDocument,
    AccessPolicy,
    AccessSubject,
    parse_access_document,
)

__all__ = [
    "ANONYMOUS_ROLE",
    "AccessConfigError",
    "AccessDocument",
    "AccessGrant",
    "AccessLookup",
    "AccessPolicy",
    "AccessSubject",
    "JsonFileAccessLookup",
    "StaticAccessLookup",
    "access_setup_errors",
    "check_access",
    "get_access_lookup",
    "get_access_subject",
    "install_access",
    "load_access_policy",
    "parse_access_document",
    "require_access",
    "route_operation_ids",
]
