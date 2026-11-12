# monitoring

The **Monitoring** domain service. It owns its business rules; other applications use them only
through this service's HTTP API and, later, its domain events (see
[ADR 0016](../../docs/adr/0016-independent-domain-services.md)).

| | |
| :--- | :--- |
| API | `/v1/...` ([openapi.json](openapi.json)) |
| Database | Shared PostgreSQL server, **own schema** `monitoring`, own roles ([roles](../../deploy/db/roles-monitoring.sql)) |
| Auth | `Authorization: Bearer <access token>` issued by the identity service, verified offline |
| Access control | Central: [`config/access-control.json`](../../config/access-control.json), service key `monitoring` ([ADR 0017](../../docs/adr/0017-central-access-control.md)) |
| Deploy unit | Own image ([Dockerfile](Dockerfile)), own Helm release ([values](../../deploy/helm/domain-service/values-monitoring.yaml)) |
| Shared code | [`platform-kit`](../../packages/platform-kit) (technical only, no business rules) |

## Layout (same names as the identity service)

| Path | What it holds |
| :--- | :--- |
| `app/core/` | `config.py` (settings), `errors.py` (application errors), `security.py` (`rate_limit`), `logging.py` |
| `app/modules/auth/dependencies.py` | `CurrentUserDep`, `get_access_subject`, `roles_of`: who is calling (bearer token) |
| `app/modules/<name>/domain/` | Entities, value objects, policies, domain errors (plain Python) |
| `app/modules/<name>/application/` | Ports (ABCs) and use cases; no FastAPI, Pydantic or SQLAlchemy |
| `app/modules/<name>/infrastructure/` | SQLAlchemy models + repositories, other adapters |
| `app/modules/<name>/router.py`, `schemas.py`, `container.py`, `public.py` | HTTP boundary, DI wiring, the module's public API |
| `app/main.py`, `api.py`, `container.py`, `models.py`, `db.py` | App + access control, router registry, composition root, model registry, declarative base |
| `tests/business_rules/` | Business-rule suite (`/generate-test-suite`), run with `uv run task test-br` |
| `tests/architecture/` | Layer rules and the access-control check |
| `tests/integrations/` | `isolated_app_transaction` (per-test rollback) and HTTP tests |
| `tests/conftest.py` | `client`, `grant_access`, `deny_access`, `db_session`, `fake_uow` (PostgreSQL in Testcontainers) |

## Commands (from this folder)

```powershell
uv sync                       # installs platform-kit from ../../packages as an editable path dependency
uv run task upgrade           # migrate the monitoring schema
uv run task dev               # http://localhost:8010/docs
uv run task check; uv run task type-check
uv run task test              # every test (needs Docker: PostgreSQL runs in Testcontainers)
uv run task test-br           # the business-rule suite only
uv run task openapi           # export openapi.json (commit it)
uv run task check-access      # every route has an operation_id, the check, and a grant
```

Image (built from the repository root so `platform-kit` and the access document are in the context):

```powershell
docker build -f services/monitoring/Dockerfile -t monitoring .
```

## Adding a module

From the specs (TDD, see `docs/index.html#quick-start`), with this layout in place:

```
specs/monitoring/
└── <module>/
    ├── service.yaml
    ├── <module>.rules.yaml
    └── <module>.domain.yaml
```

```
/generate-test-suite   specs/monitoring/<module>
/generate-source-code  specs/monitoring/<module> core
/generate-source-code  specs/monitoring/<module> api
```

Rules that always hold: every route has a stable camelCase `operation_id=` and `rate_limit(...)`, and is
granted in `config/access-control.json` under `"monitoring"`; never check roles in code; ownership stays in
the use cases; never read another service's schema (call its API through `platform_kit.http.client.ServiceClient`).
