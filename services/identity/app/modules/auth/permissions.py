"""
Role-based access control (RBAC).

Roles are owned by the users domain (`Role`, a value object of the account); this module decides
what each role may do. Permissions are `<resource>:<action>` strings checked with `require_permission(...)` (see
`app.modules.auth.dependencies`). Roles map to permission sets here, in code, so changes are reviewed
and versioned; `"*"` grants everything. Resource *ownership* (a user may only touch their own todos)
is enforced separately by `check_ownership(...)`.

To add a permission: add it to `Permission`, grant it to roles below, and protect the route with
`dependencies=[require_permission(Permission.X)]`.
"""

from enum import StrEnum

from app.modules.users.public import Role

__all__ = ["ROLE_PERMISSIONS", "Permission", "Role", "has_permission"]


class Permission(StrEnum):
    USERS_READ_ALL = "users:read_all"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.USER: frozenset(),
    Role.ADMIN: frozenset({"*"}),
}


def has_permission(role: str, permission: str) -> bool:
    granted = ROLE_PERMISSIONS.get(role, frozenset())
    return "*" in granted or permission in granted
