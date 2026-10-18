# 0009. Authorization: RBAC in code plus central ownership checks

- Status: Accepted
- Date: 2026-10-16

## Context

Authorization was limited to "is the caller the owner of this resource", implemented per route. There was no notion of roles or administrative capabilities.

## Decision

- Each user has a `role` (`users.role`, default `user`). Roles map to permission strings (`<resource>:<action>`) in `app/modules/auth/permissions.py`; `"*"` grants everything (`admin`). Keeping the mapping in code makes changes reviewable and versioned with the code that relies on them.
- Routes declare required permissions with `dependencies=[require_permission(Permission.X)]`; failures return 403 `forbidden`.
- Resource ownership stays a separate, central check: `check_ownership("<module>.service", "<path_param>")` loads the resource and compares `user_id` with the caller (404 if missing, 403 if not owned).
- Both live in the auth module (`dependencies.py`), so every access-control decision is in one place and other modules only declare what they need.

## Consequences

- Promoting an admin is a data change (`UPDATE users SET role = 'admin' ...`), ideally via an audited admin command.
- When roles must be configurable at runtime or per tenant, move `ROLE_PERMISSIONS` to tables (`roles`, `role_permissions`) behind the same `has_permission` function, or adopt ABAC/ReBAC (e.g. OPA, OpenFGA) behind `require_permission`; routes don't change.
