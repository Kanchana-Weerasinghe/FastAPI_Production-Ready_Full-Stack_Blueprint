# 0003. URL major versioning and deprecation policy

- Status: Accepted
- Date: 2026-10-16

## Context

Clients (web, mobile, partners) upgrade at different speeds. We need a predictable way to evolve the API without breaking them, and a clear definition of what counts as breaking.

## Decision

- The major version is part of the URL (`/v1`, `/v2`), mounted in `app/api.py`. Routers inside a module are version-agnostic; `app/api.py` decides which version exposes them.
- **Non-breaking** changes ship in place: new endpoints, new optional request fields, new response fields, new error `code`s, relaxed validation.
- **Breaking** changes require a new major version: removing/renaming fields or endpoints, changing types or semantics, making optional input required, tightening validation, changing error codes.
- A deprecated endpoint keeps working for at least 6 months after announcement and responds with `Deprecation` (RFC 9745) and `Sunset` (RFC 8594) headers plus a `Link: <docs>; rel="deprecation"` header. Usage of deprecated endpoints is tracked in logs/metrics before removal.
- The OpenAPI document is the contract; CI fails on breaking diffs against `main` unless the version is bumped.

## Consequences

- At most two major versions are supported at the same time.
- Note: in this template `/v1` currently hosts auth and `/v2` the resource APIs for historical reasons; new modules are mounted under the latest version.
