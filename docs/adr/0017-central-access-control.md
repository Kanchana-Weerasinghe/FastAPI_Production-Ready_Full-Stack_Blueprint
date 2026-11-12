# 0017. Central access control: data-driven, deny by default

- Status: Accepted
- Date: 2026-11-12
- Supersedes: [0009](0009-authorization-rbac.md) (the role → permission table in code); its ownership check stays

## Context

Who may call which endpoint was decided in code: `ROLE_PERMISSIONS` and `Permission` in
`app/modules/auth/permissions.py`, `require_permission(...)` on individual routes, and role names in the
code of other services (`is_admin`, role constants). Changing access needed a code change, review and deploy, and an
endpoint without a `require_permission` was open to every signed-in caller. Access must change without a
code change, be evaluated the same way in every service, and later work with Azure AD (Entra ID) tokens.

## Decision

- **Model.** `Role ──< Privilege (a feature) ──< Endpoint (service, operationId)`. Every caller also
  holds the implicit `anonymous` role, so public endpoints are simply granted to `anonymous`.
- **Store.** One central document for all services, [`config/access-control.json`](../../config/access-control.json),
  shaped like the future tables (`roles`, `privileges`, `privilege_endpoints`, `role_privileges`). It is
  baked into each image at `/app/config/access-control.json` (`ACCESS_CONFIG_PATH`) and can be replaced per
  environment by a ConfigMap (Helm `accessControl.document`). Services re-read it when it changes
  (`ACCESS_RELOAD_SECONDS`); a broken edit is logged and the last valid version stays in force.
- **Endpoint key.** The FastAPI `operation_id` (= OpenAPI `operationId`), camelCase, unique per service and
  never renamed. URL paths are not used: they carry versions and parameters.
- **One check.** `platform_kit.access.require_access()`, applied once per router:
  `APIRouter(..., dependencies=[require_access()])`. It reads the matched route's `operation_id` and allows
  the call only if a role of the caller holds it.
  - not granted, caller not signed in → **401** (the credential's own code, e.g. `token_expired`);
  - not granted to a signed-in caller → **403 `access_denied`**;
  - endpoint in no privilege, or policy unavailable → refused (deny by default, fail closed).
- **Wiring.** Each service calls `install_access(app, subject=..., lookup=...)` after mounting its routers.
  `subject` resolves the caller to an `AccessSubject` (identity: the session cookie; the account's role).
  Startup is refused if a route lacks an `operation_id` or the check, an `operation_id` is duplicated, or the
  document grants an operation the service does not have. An architecture test runs the same validation.
- **Principal → roles** is one function (identity: `roles_of` in `app/modules/auth/dependencies.py`). With
  Azure AD only this function changes (token `groups` / `oid` → roles).
- **Ownership stays in code.** "Only the owner may …" is a row-level business rule (`check_ownership`,
  404 for strangers in the use cases), not access control.
- **Checks inside use cases** that are not an endpoint (e.g. "may act on any owner's records") are declared
  operations in the document, passed to `install_access(extra_operations=...)` and asked with
  `AccessGrant.allows("<operation>")`; never a role name.
- **Tests.** `grant_access(*operation_ids)` / `deny_access()` fixtures replace the document (the lookup),
  never the check, so the real `require_access` runs. Public endpoints stay open in both.

## Consequences

- Changing who may call what is an edit of one JSON file (or ConfigMap), reviewed in Git, with no code change.
  A new endpoint is refused until it is granted.
- The user's `role` (`user` / `admin`) stays on the account as the role the access check sees; it no
  longer means anything by itself. `scripts/create_admin.py` still bootstraps the first `admin`.
- Refusals change from 403 `forbidden` to 403 `access_denied`.
- Identity now depends on `platform-kit` and its image is built from the repository root
  (`docker build -f services/identity/Dockerfile .`).
- **Later:** an `access` module in identity with the same tables and an admin API (seeded from this
  document) replaces the file; services switch from `JsonFileAccessLookup` to a lookup that fetches their
  part from identity. Routes, use cases and tests do not change.
