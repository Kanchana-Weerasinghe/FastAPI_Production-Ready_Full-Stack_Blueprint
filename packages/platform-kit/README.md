# platform-kit

Technical building blocks shared by the domain services in `services/`. It contains **no business
rules**: each service keeps its own `domain/` and `application/` layers and imports this package only
for cross-cutting concerns.

| Module | Provides |
| :--- | :--- |
| `settings` | `ServiceSettings` base (DB, schema, JWT verification, HTTP); fails closed in staging/production |
| `logging` | Structured JSON logs with service/version/env, secret and email redaction |
| `database` | `Database` (schema-bound engine), `UnitOfWork` with `after_commit` |
| `persistence` | `schema_metadata(schema)`, `AuditColumnsMixin` (id, timestamps, version) |
| `errors` | Framework-agnostic `AppError` hierarchy (safe to use from domain code) |
| `auth` | `TokenVerifier` for core-api access tokens, `Principal`, `bearer_token` |
| `http.app` | `create_service_app(...)`: handlers, middleware, CORS, health, routers |
| `http.middleware` | Request ID propagation, body limit, one transaction per request (rollback on 4xx/5xx) |
| `http.problems` | RFC 9457 Problem Details handlers |
| `http.health` | `/health/live`, `/health/ready` |
| `http.conditional` | `ETag` / `If-Match` helpers |
| `http.pagination` | `CamelModel`, `PageParams` (capped), `PageInfo` |
| `http.client` | `ServiceClient` for calling another service (timeouts, token + request-ID forwarding) |

Services depend on it as an editable path dependency:

```toml
[tool.uv.sources]
platform-kit = { path = "../../packages/platform-kit", editable = true }
```

Changes here affect every service: keep it backward compatible, version it (`version` in
`pyproject.toml`), and run each service's tests before merging. When services move to separate
repositories, publish it to a private package index and pin versions instead.

```powershell
uv sync; uv run task check; uv run task type-check; uv run task test
```
