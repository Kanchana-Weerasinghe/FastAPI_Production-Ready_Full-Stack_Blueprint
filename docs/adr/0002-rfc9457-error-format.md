# 0002. Domain errors rendered as RFC 9457 Problem Details

- Status: Accepted
- Date: 2026-10-16

## Context

Errors were `HTTPException` subclasses raised from services, coupling business code to HTTP, and the response body was a custom `{status, type, message}` shape with no stable machine-readable code. Clients had to match on English messages, and framework errors (404 route, 405) used a different shape.

## Decision

- Business code raises framework-agnostic errors from `app/core/errors.py` (`BadRequestError`, `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`, `ConflictError`, `PayloadTooLargeError`, `ServiceUnavailableError`). Each has an HTTP `status`, a default `code` and `title`; call sites may pass a more specific `code` (e.g. `attachment_not_found`) and RFC 9457 extension members via `extra`.
- `app/core/error_handlers.py` renders **every** error (domain, framework HTTP, validation, rate limit, unhandled) as `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, `code`, `request_id`, plus `errors[]` for validation failures.
- `type` is `PROBLEM_TYPE_BASE_URI/<code>`; point the base URI at your public error documentation.
- `code` values are a public contract: never rename or reuse one; add new codes instead.
- Unhandled exceptions return a generic 500 and are logged with the traceback; internal details are never returned.

## Consequences

- Clients (and the generated TypeScript client) can branch on `code`, and support can correlate any error via `request_id`.
- Business code can be reused from workers/CLIs without HTTP types.
- Breaking change for clients that parsed the old `message`/`type` fields (the bundled web app does not).
