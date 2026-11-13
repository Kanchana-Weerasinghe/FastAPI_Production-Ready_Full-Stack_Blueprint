r'''
The service skeleton both generators create (paths relative to services/<service>/).

It has the same layout and names as the identity service wherever the generate-test-suite and
generate-source-code skills look for them: `app/core/config.py`, `app/core/errors.py`,
`app/core/security.py` (`rate_limit`), `app/modules/auth/dependencies.py` (`CurrentUserDep`,
`get_access_subject`, `roles_of`), and the test fixtures `client`, `grant_access`, `deny_access`,
`db_session`, `fake_uow` and `isolated_app_transaction`. Placeholders are `{{name}}` tokens.
'''

from pathlib import Path

# Swagger UI with a "Graph" button per operation (development only); copied as is, no tokens.
_CODE_GRAPHS = (Path(__file__).parent / "assets" / "code_graphs.py").read_text(encoding="utf-8")

BASE_FILES: dict[str, str] = {
    ".python-version": "3.12\n",
    ".env.example": r'''# Copy to `services/{{service}}/.env` for local development (never commit it).
ENVIRONMENT=development
SERVICE_NAME={{service}}
LOG_LEVEL=INFO

# --- Database: same PostgreSQL server as the identity service, but this service's own schema (and, when deployed, its own role) ---
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USERNAME=root
DB_PASSWORD=password
DB_SCHEMA={{service_snake}}

# --- Token verification: must equal the identity service's SECRET_KEY (the identity service issues the access tokens) ---
JWT_SECRET_KEY=dev-insecure-secret-key-change-me

# --- Access control: defaults to the repository's config/access-control.json ---
# ACCESS_CONFIG_PATH=../../config/access-control.json
ACCESS_RELOAD_SECONDS=30

# --- Rate limiting (memory:// per process; redis://... to share counters across workers and replicas) ---
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=memory://

# --- HTTP ---
PROBLEM_TYPE_BASE_URI=https://errors.example.com
CORS_ORIGINS=["http://localhost:3000"]

# --- Business configuration ---
''',
    "Dockerfile": r'''# syntax=docker/dockerfile:1.7
# Production image for {{service}}.
# Build from the repository root so the shared platform-kit package and the central access document
# are in the context:
#   docker build -f services/{{service}}/Dockerfile -t {{service}} .

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    # Create the venv at its final path: console-script shebangs embed the venv location.
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

# Same relative layout as the repository, so the `../../packages/platform-kit` path source resolves.
WORKDIR /src
COPY packages/platform-kit ./packages/platform-kit
COPY services/{{service}}/pyproject.toml services/{{service}}/uv.lock ./services/{{service}}/
WORKDIR /src/services/{{service}}
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable


FROM ${PYTHON_IMAGE} AS runtime

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="{{service}}" \
      org.opencontainers.image.version="${APP_VERSION}"

# ACCESS_CONFIG_PATH: the central access document; mount a ConfigMap over it to change access without a rebuild.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION} \
    ACCESS_CONFIG_PATH=/app/config/access-control.json

RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --chown=root:root config/access-control.json ./config/access-control.json
COPY --chown=root:root services/{{service}}/alembic.ini ./
COPY --chown=root:root services/{{service}}/app ./app
COPY --chown=root:root services/{{service}}/migrations ./migrations

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--graceful-timeout", "30"]
''',
    "Dockerfile.dockerignore": r'''# Used by `docker build -f services/{{service}}/Dockerfile .` (the build context is the repo root).
# Allow-list: only the shared package, the central access document and this service reach the context.
*
!packages/platform-kit/
!config/access-control.json
!services/{{service}}/
**/.venv
**/__pycache__
**/*.pyc
**/.mypy_cache
**/.ruff_cache
**/.pytest_cache
**/.coverage
**/.env
**/.env.*
services/{{service}}/tests/
packages/platform-kit/tests/
''',
    "README.md": r'''# {{service}}

The **{{service_title}}** domain service. It owns its business rules; other applications use them only
through this service's HTTP API and, later, its domain events (see
[ADR 0016](../../docs/adr/0016-independent-domain-services.md)).

| | |
| :--- | :--- |
| API | `/v1/...` ([openapi.json](openapi.json)) |
| Database | Shared PostgreSQL server, **own schema** `{{service_snake}}`, own roles ([roles](../../deploy/db/roles-{{service}}.sql)) |
| Auth | `Authorization: Bearer <access token>` issued by the identity service, verified offline |
| Access control | Central: [`config/access-control.json`](../../config/access-control.json), service key `{{service}}` ([ADR 0017](../../docs/adr/0017-central-access-control.md)) |
| Deploy unit | Own image ([Dockerfile](Dockerfile)), own Helm release ([values](../../deploy/helm/domain-service/values-{{service}}.yaml)) |
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
uv run task upgrade           # migrate the {{service_snake}} schema
uv run task dev               # http://localhost:{{port}}/docs
uv run task check; uv run task type-check
uv run task test              # every test (needs Docker: PostgreSQL runs in Testcontainers)
uv run task test-br           # the business-rule suite only
uv run task openapi           # export openapi.json (commit it)
uv run task check-access      # every route has an operation_id, the check, and a grant
```

Image (built from the repository root so `platform-kit` and the access document are in the context):

```powershell
docker build -f services/{{service}}/Dockerfile -t {{service}} .
```

## Adding a module

From the specs (TDD, see `docs/index.html#quick-start`), with this layout in place:

```
specs/{{service}}/
└── <module>/
    ├── service.yaml
    ├── <module>.rules.yaml
    └── <module>.domain.yaml
```

```
/generate-test-suite   specs/{{service}}/<module>
/generate-source-code  specs/{{service}}/<module> core
/generate-source-code  specs/{{service}}/<module> api
```

Rules that always hold: every route has a stable camelCase `operation_id=` and `rate_limit(...)`, and is
granted in `config/access-control.json` under `"{{service}}"`; never check roles in code; ownership stays in
the use cases; never read another service's schema (call its API through `platform_kit.http.client.ServiceClient`).
''',
    "alembic.ini": r'''[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''',
    "pyproject.toml": r'''[project]
name = "{{service}}"
version = "0.1.0"
description = "{{service_title}} domain service: owns its business rules (see README.md)."
requires-python = ">=3.12"
dependencies = [
    "platform-kit",
    "alembic>=1.18.4",
    "dependency-injector>=4.49.0",
    "fastapi[standard]>=0.135.3",
    "gunicorn>=23",
    "slowapi>=0.1.9",
    "uvicorn>=0.44.0",
]

[tool.uv.sources]
platform-kit = { path = "../../packages/platform-kit", editable = true }
codegraphs = { path = "../../../codegraphs", editable = true }

[dependency-groups]
dev = [
    "codegraphs",
    "mypy>=1.20.1",
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.1.0",
    "pyyaml>=6.0.2",
    "ruff>=0.15.10",
    "taskipy>=1.14.0",
    "testcontainers[postgres]>=4.15.0",
    "types-pyyaml>=6.0.12",
]

[tool.taskipy.tasks]
dev = "fastapi dev app/main.py --port {{port}}"
openapi = "python scripts/export_openapi.py"
check-access = "python scripts/check_access.py"
upgrade = "alembic upgrade head"
downgrade = "alembic downgrade -1"
format = "ruff format . && ruff check --fix ."
check = "ruff check . && ruff format --check ."
type-check = "mypy ."
test = "pytest -v"
test-br = "pytest tests/business_rules -v"
cov = "pytest --cov=app --cov-report=term-missing"
cov-html = "pytest --cov=app --cov-report=html"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
filterwarnings = ["ignore::DeprecationWarning"]

[tool.coverage.run]
source = ["app"]
concurrency = ["greenlet", "thread"]

[tool.coverage.report]
show_missing = true
fail_under = 90

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "PT"]
ignore = ["E501", "B008"]

[tool.ruff.lint.per-file-ignores]
"scripts/*.py" = ["E402"]
"app/core/security.py" = ["ARG001"]
"app/modules/*/router.py" = ["ARG001"]
"tests/conftest.py" = ["E402"]
"tests/**/conftest.py" = ["ARG001"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
exclude = ["migrations/"]
''',
    # --- app/core ------------------------------------------------------------------------------
    "app/__init__.py": r'''"""The {{service}} domain service."""
''',
    "app/core/__init__.py": "",
    "app/core/config.py": r'''"""Settings of the {{service}} service: environment variables, then a local `.env`."""

from pathlib import Path

from platform_kit.settings import ServiceSettings

_SERVICE_DIR = Path(__file__).resolve().parents[2]


class Settings(ServiceSettings):
    SERVICE_NAME: str = "{{service}}"
    DB_SCHEMA: str = "{{service_snake}}"
    # The central access document (config/access-control.json in the repository). The image sets
    # ACCESS_CONFIG_PATH=/app/config/access-control.json; mount a ConfigMap over it to change access.
    ACCESS_CONFIG_PATH: str = str(_SERVICE_DIR.parent.parent / "config" / "access-control.json")

    # --- Rate limiting: memory:// counts per process; use redis://... to share counters across replicas ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # --- Business configuration ---


config = Settings()
''',
    "app/core/errors.py": r'''"""
Application errors of this service: the framework-agnostic platform-kit types, re-exported so every
module imports them from one place (like the identity service's `app.core.errors`).

Each maps to an RFC 9457 problem response with its `status` and a stable `code`. Never raise
`HTTPException` outside a router.

| Status | Class |
| :--- | :--- |
| 400 | BadRequestError |
| 401 | AuthenticationError |
| 403 | PermissionDeniedError (AccessDeniedError is the central access check's) |
| 404 | NotFoundError |
| 409 | ConflictError |
| 412 | PreconditionFailedError |
| 422 | UnprocessableError |
| 503 | ServiceUnavailableError |
"""

from platform_kit.errors import (
    AccessDeniedError,
    AppError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PreconditionFailedError,
    ServiceUnavailableError,
    UnprocessableError,
)

__all__ = [
    "AccessDeniedError",
    "AppError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "NotFoundError",
    "PermissionDeniedError",
    "PreconditionFailedError",
    "ServiceUnavailableError",
    "UnprocessableError",
]
''',
    "app/core/logging.py": r'''"""The structured logger (platform-kit), importable from `app.core` like in the identity service."""

from platform_kit.logging import logger

__all__ = ["logger"]
''',
    "app/core/security.py": r'''"""
Rate limiting: the same `rate_limit(...)` dependency as the identity service.

    @router.get("/", operation_id="listThings", dependencies=[rate_limit("200/minute")])

Limits count per client address. Set RATE_LIMIT_STORAGE_URI to Redis so they hold across gunicorn
workers and replicas; RATE_LIMIT_ENABLED=false turns them off (tests, the QA suite).
"""

from typing import Any

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import config

limiter = Limiter(key_func=get_remote_address, storage_uri=config.RATE_LIMIT_STORAGE_URI)


def rate_limit(limit_value: str) -> Any:
    """FastAPI dependency factory for rate limiting, e.g. `rate_limit("60/minute")`."""

    async def dependency(request: Request) -> None:
        pass

    if not config.RATE_LIMIT_ENABLED:
        return Depends(dependency)

    func_name = f"dependency_{id(dependency)}"
    dependency.__name__ = func_name
    dependency.__qualname__ = f"rate_limit.<locals>.{func_name}"
    return Depends(limiter.limit(limit_value)(dependency))
''',
    # --- app/devtools: development-only Swagger UI with code graphs -------------------------------
    "app/devtools/__init__.py": r'''"""Local-development tooling mounted by the composition root; never enabled outside development."""
''',
    "app/devtools/code_graphs.py": _CODE_GRAPHS,
    "codegraphs.toml": r'''# Code graphs for the {{service}} service (the "Graph" button in /docs during development). Regenerate with:
#   uv run codegraphs run --config codegraphs.toml
src = "app"
prefix = "app"
out = "docs/code-graphs"
title = "{{service_title}} service"
exclude = []
''',
    # --- app --------------------------------------------------------------------------------
    "app/api.py": r'''"""Router registry: every module router is mounted here under its API version."""

from fastapi import APIRouter

api_v1 = APIRouter(prefix="/v1")

API_ROUTERS = [api_v1]
''',
    "app/container.py": r'''from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.core.config import config


class Container(containers.DeclarativeContainer):
    """Composition root: shared infrastructure plus one sub-container per module."""

    wiring_config = containers.WiringConfiguration(packages=["app.modules"])

    db = providers.Singleton(
        Database,
        url=config.database_url,
        schema=config.DB_SCHEMA,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
        statement_timeout_ms=config.DB_STATEMENT_TIMEOUT_MS,
    )
    uow = providers.Factory(UnitOfWork, db=db)
''',
    "app/db.py": r'''"""The service's declarative base: every table lives in this service's own schema."""

from platform_kit.persistence import schema_metadata
from sqlalchemy.orm import DeclarativeBase

from app.core.config import config


class Base(DeclarativeBase):
    metadata = schema_metadata(config.DB_SCHEMA)
''',
    "app/models.py": r'''"""Model registry for Alembic and tests: import every module's ORM models here."""

from app.db import Base

__all__ = ["Base"]
''',
    "app/main.py": r'''from fastapi import Request
from fastapi.responses import JSONResponse
from platform_kit.access import JsonFileAccessLookup, install_access
from platform_kit.http.app import create_service_app
from platform_kit.http.problems import problem_response
from platform_kit.logging import setup_logging
from slowapi.errors import RateLimitExceeded

from app.api import API_ROUTERS
from app.container import Container
from app.core.config import config
from app.core.security import limiter
from app.devtools.code_graphs import install_dev_docs
from app.modules.auth.dependencies import get_access_subject

# Routes outside access control (probes, the development-only docs and code-graph tools). Every other
# route must carry an operation_id and pass `require_access()`; the service refuses to start otherwise.
ACCESS_EXEMPT_PATH_PREFIXES = ("/health", "/docs", "/admin/code-graphs")

setup_logging(
    service=config.SERVICE_NAME, version=config.APP_VERSION, environment=config.ENVIRONMENT, level=config.LOG_LEVEL
)

container = Container()
db = container.db()

app = create_service_app(
    settings=config,
    db=db,
    routers=API_ROUTERS,
    title="{{service_title}} API",
    description="The {{service_title}} domain service.",
    docs_url=None,  # served below in development: Swagger UI with a "Graph" button per operation
)
if config.ENVIRONMENT == "development":
    install_dev_docs(app, openapi_url=app.openapi_url or "/openapi.json")
app.state.container = container
app.state.limiter = limiter


async def _rate_limited(request: Request, _exc: Exception) -> JSONResponse:
    return problem_response(
        request,
        base_uri=config.PROBLEM_TYPE_BASE_URI,
        status=429,
        code="rate_limited",
        title="Too Many Requests",
        detail="Too many requests. Please try again later.",
    )


app.add_exception_handler(RateLimitExceeded, _rate_limited)

# Central access control: who may call which operation is data in config/access-control.json.
install_access(
    app,
    subject=get_access_subject,
    lookup=JsonFileAccessLookup(
        config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME, reload_seconds=config.ACCESS_RELOAD_SECONDS
    ),
    exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES,
)
''',
    "app/modules/__init__.py": "",
    "app/modules/auth/__init__.py": r'''"""Caller resolution (not a business module): see dependencies.py."""
''',
    "app/modules/auth/dependencies.py": r'''"""
Who is calling, from `Authorization: Bearer <access token>` issued by the identity service (verified
offline by `platform_kit.auth`). Same names as the identity service's auth dependencies:

- `get_access_subject`: the caller as the central access check sees it (`require_access()` on every
  router). Never raises for bad credentials, so public endpoints keep working.
- `CurrentUserDep`: the signed-in caller (`Principal`: `user_id`, `role`, `token`) for routes that need
  the user ID, e.g. to pass the acting user to a use case.
- `roles_of(...)`: the single place that maps a caller to the roles named in config/access-control.json.

Ownership ("only the owner may ...") is a business rule and stays in the use cases. Never check a role
in code.
"""

from typing import Annotated

from fastapi import Depends, Header
from platform_kit.access import AccessSubject
from platform_kit.auth import Principal, TokenVerifier, bearer_token
from platform_kit.errors import AuthenticationError

from app.core.config import config

_verifier = TokenVerifier(secret_key=config.JWT_SECRET_KEY.get_secret_value(), algorithm=config.JWT_ALGORITHM)


def roles_of(principal: Principal) -> frozenset[str]:
    """The roles a caller holds, as named in the access document (today: the token's `role` claim)."""
    return frozenset({principal.role})


async def get_current_user(authorization: Annotated[str | None, Header()] = None) -> Principal:
    return _verifier.verify(bearer_token(authorization))


async def get_access_subject(authorization: Annotated[str | None, Header()] = None) -> AccessSubject:
    try:
        principal = _verifier.verify(bearer_token(authorization))
    except AuthenticationError as e:
        return AccessSubject.anonymous(e)
    return AccessSubject.signed_in(roles_of(principal))


CurrentUserDep = Annotated[Principal, Depends(get_current_user)]
''',
    # --- migrations ---------------------------------------------------------------------------
    "migrations/env.py": r'''"""
Alembic environment for this service's own schema.

The schema and the `alembic_version` table both live in `DB_SCHEMA`, so this service migrates
independently of every other service sharing the same PostgreSQL server.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import config as settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
SCHEMA = settings.DB_SCHEMA


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=lambda name, type_, _parent: type_ != "schema" or name == SCHEMA,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=settings.database_url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
''',
    "migrations/script.py.mako": r'''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
''',
    "migrations/versions/.gitkeep": "",
    # --- scripts ------------------------------------------------------------------------------
    "scripts/export_openapi.py": r'''"""
Exports this service's OpenAPI contract to `services/{{service}}/openapi.json`.

    uv run python scripts/export_openapi.py            # write
    uv run python scripts/export_openapi.py --check    # exit 1 if the committed file is stale
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

TARGET = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> int:
    document = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != document:
            print("openapi.json is out of date: run `uv run task openapi` and commit it.")
            return 1
        return 0
    TARGET.write_text(document, encoding="utf-8")
    print(f"Wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "scripts/check_access.py": r'''"""
Checks this service against the central access document (config/access-control.json):
every route has an operation_id and `require_access()`, the document names no unknown operation of
this service, and every operation is granted to at least one role.

    uv run python scripts/check_access.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from platform_kit.access import access_setup_errors, load_access_policy, route_operation_ids

from app.core.config import config
from app.main import ACCESS_EXEMPT_PATH_PREFIXES, app


def main() -> int:
    policy = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    errors = access_setup_errors(app, policy=policy, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    operations = route_operation_ids(app, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    errors += [
        f"operation {operation!r} is not granted to any role in {config.ACCESS_CONFIG_PATH}"
        for operation in sorted(operations - policy.operations)
    ]
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    # --- tests --------------------------------------------------------------------------------
    "tests/__init__.py": "",
    "tests/_database_safety.py": r'''from collections.abc import Mapping


def reject_external_test_database(environment: Mapping[str, str]) -> None:
    """Prevents schema-resetting tests from connecting to a shared or developer-managed database."""
    if environment.get("TEST_DB_HOST"):
        raise RuntimeError(
            "TEST_DB_HOST is not supported: tests recreate the schema and must use an isolated Testcontainers database."
        )
''',
    "tests/conftest.py": r'''"""
Shared test fixtures, named like the identity service's (the generate-test-suite skill copies its patterns).

- PostgreSQL runs in a throwaway Testcontainers container (Docker required), configured BEFORE any app
  module is imported, because settings are read at import.
- `client`: `await client()` is anonymous; `await client(user_id=..., role=...)` sends a bearer token like
  the ones the identity service issues (role defaults to "user").
- `grant_access(*operation_ids)` / `deny_access()`: replace the access document for one test; the real
  `require_access()` check still runs.
- `db_session`: a session inside a transaction rolled back after the test (repository tests).
- `fake_uow`: an in-memory UnitOfWork that records after-commit callbacks (`await fake_uow.commit()` runs them).

Integration tests also import `isolated_app_transaction` from tests/integrations/conftest.py.
"""

import os
import sys
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from testcontainers.postgres import PostgresContainer

from tests._database_safety import reject_external_test_database

TEST_JWT_SECRET = "test-secret-key-that-is-at-least-32-characters-long"
_postgres_container: PostgresContainer | None = None


def _configure_test_database() -> None:
    global _postgres_container
    reject_external_test_database(os.environ)
    if sys.platform == "win32":
        # Ryuk's port mapping is unreliable on Docker Desktop for Windows; the container is
        # stopped explicitly in `pytest_sessionfinish` instead.
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    _postgres_container = PostgresContainer(
        "postgres:16-alpine", username="test", password="test", dbname="app_test", driver=None
    )
    _postgres_container.start()
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "DB_HOST": _postgres_container.get_container_host_ip(),
            "DB_PORT": str(_postgres_container.get_exposed_port(5432)),
            "DB_USERNAME": "test",
            "DB_PASSWORD": "test",
            "DB_NAME": "app_test",
            "JWT_SECRET_KEY": TEST_JWT_SECRET,
            "RATE_LIMIT_ENABLED": "false",
        }
    )


_configure_test_database()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _postgres_container is not None:
        _postgres_container.stop()


import jwt
from httpx import ASGITransport, AsyncClient
from platform_kit.access import ANONYMOUS_ROLE, load_access_policy
from platform_kit.access.testing import AccessOverride, override_access
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import config
from app.main import app as app_instance
from app.models import Base
from tests.mocks.uow import FakeUnitOfWork

ClientFactory = Callable[..., Awaitable[AsyncClient]]

engine = create_async_engine(
    config.database_url,
    connect_args={"server_settings": {"search_path": config.DB_SCHEMA, "timezone": "UTC"}},
)


def access_token(*, user_id: uuid.UUID | None = None, role: str = "user") -> str:
    """An access token shaped like the identity service's, signed with the test secret."""
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id or uuid.uuid4()),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{config.DB_SCHEMA}"'))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[ClientFactory, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app_instance, raise_app_exceptions=False),
        base_url="http://localhost",
    ) as client_instance:

        async def _client(*, user_id: uuid.UUID | None = None, role: str | None = None) -> AsyncClient:
            client_instance.headers.pop("Authorization", None)
            if user_id is not None or role is not None:
                token = access_token(user_id=user_id, role=role or "user")
                client_instance.headers["Authorization"] = f"Bearer {token}"
            return client_instance

        yield _client


# --- Access control: replace the access document for one test; the real `require_access` still runs ---


@pytest.fixture
def _access_override() -> Iterator[AccessOverride]:
    # Public endpoints stay open, so anonymous calls behave as in production.
    document = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    public = document.role_operations.get(ANONYMOUS_ROLE, frozenset())
    with override_access(app_instance, service=config.SERVICE_NAME, public=public) as access:
        yield access


@pytest.fixture
def grant_access(_access_override: AccessOverride) -> Callable[..., None]:
    """`grant_access("listThings", ...)`: the signed-in test caller may call exactly these operationIds."""
    return _access_override.grant


@pytest.fixture
def deny_access(_access_override: AccessOverride) -> Callable[[], None]:
    """`deny_access()`: the signed-in test caller may call nothing (public endpoints stay open)."""
    return _access_override.deny


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session wrapped in a transaction that is rolled back after each test."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()
''',
    "tests/mocks/__init__.py": "",
    "tests/mocks/uow.py": r'''from collections.abc import Awaitable, Callable
from typing import Any


class FakeUnitOfWork:
    """In-memory stand-in for UnitOfWork: records after-commit callbacks so tests can assert or run them."""

    def __init__(self) -> None:
        self.callbacks: list[tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]] = []

    def after_commit(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        self.callbacks.append((func, args, kwargs))

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        """Simulates a successful commit by running and clearing the registered callbacks."""
        callbacks, self.callbacks = self.callbacks, []
        for func, args, kwargs in callbacks:
            await func(*args, **kwargs)
''',
    "tests/integrations/__init__.py": "",
    "tests/integrations/conftest.py": r'''from collections.abc import AsyncGenerator

import pytest

from app.main import db


@pytest.fixture(autouse=True)
async def isolated_app_transaction() -> AsyncGenerator[None, None]:
    """
    Runs each integration test inside an outer transaction that is rolled back afterwards.

    The app's sessions are bound to that connection with `create_savepoint`, so every
    request-level commit only releases a SAVEPOINT and no test can leak data into the next.
    """
    session_factory = db._session_factory
    async with db._engine.connect() as connection:
        transaction = await connection.begin()
        session_factory.configure(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield
        finally:
            session_factory.configure(bind=db._engine, join_transaction_mode="conservative_savepoint")
            await transaction.rollback()
''',
    "tests/integrations/test_health.py": r'''from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

ClientFactory = Callable[..., Awaitable[AsyncClient]]


async def test_service_is_live(client: ClientFactory) -> None:
    http = await client()
    response = await http.get("/health/live")
    assert response.status_code == 200


async def test_service_is_ready_with_its_database(client: ClientFactory) -> None:
    http = await client()
    response = await http.get("/health/ready")
    assert response.status_code == 200
''',
    "tests/business_rules/__init__.py": "",
    "tests/business_rules/conftest.py": r'''import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "br(rule_id, case_id): links a test to a business rule and test case")
''',
    "tests/architecture/__init__.py": "",
    "tests/architecture/test_layers.py": r'''"""
Layer rules for this service, enforced on every test run:

- domain/: plain Python; may use `platform_kit.errors` only (framework-agnostic error types).
- application/: may use domain, its own ports, `app.core` and framework-free platform-kit parts; never
  infrastructure, web frameworks, ORMs or HTTP clients.
- Modules talk to each other only through `public.py` (and use `app.modules.auth.dependencies` for the caller).
- No module imports another service's code: other services are reached over HTTP or events.
"""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
# Technical modules that are not business modules (no layers).
SUPPORT_MODULES = {"auth"}
MODULES = sorted(
    p
    for p in (APP_DIR / "modules").iterdir()
    if p.is_dir() and not p.name.startswith("__") and p.name not in SUPPORT_MODULES
)

FORBIDDEN_IN_DOMAIN = ("fastapi", "starlette", "pydantic", "sqlalchemy", "httpx", "dependency_injector", "app.core")
FORBIDDEN_IN_APPLICATION = ("fastapi", "starlette", "pydantic", "sqlalchemy", "httpx", "dependency_injector")
ALLOWED_PLATFORM_IN_DOMAIN = ("platform_kit.errors",)
ALLOWED_PLATFORM_IN_APPLICATION = ("platform_kit.errors", "platform_kit.auth", "platform_kit.logging")
ALLOWED_CROSS_MODULE = ("app.modules.auth.dependencies",)
OTHER_SERVICES = ("identity",)


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _starts(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in prefixes)


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_module_has_layers(module: Path) -> None:
    for layer in ("domain", "application/ports", "application/use_cases", "infrastructure/persistence"):
        assert (module / layer).is_dir(), f"{module.name} is missing {layer}/"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_domain_is_framework_free(module: Path) -> None:
    for path in (module / "domain").rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, FORBIDDEN_IN_DOMAIN), f"{path.relative_to(APP_DIR)} imports {name}"
            assert not name.startswith("app.modules.") or ".domain" in name, f"{path} imports {name}"
            if name.startswith("platform_kit"):
                assert _starts(name, ALLOWED_PLATFORM_IN_DOMAIN), f"{path} imports {name}"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_application_does_not_depend_on_infrastructure(module: Path) -> None:
    for path in (module / "application").rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, FORBIDDEN_IN_APPLICATION), f"{path.relative_to(APP_DIR)} imports {name}"
            assert ".infrastructure" not in name, f"{path.relative_to(APP_DIR)} imports {name}"
            if name.startswith("platform_kit"):
                assert _starts(name, ALLOWED_PLATFORM_IN_APPLICATION), f"{path} imports {name}"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_modules_use_each_others_public_api_only(module: Path) -> None:
    for path in module.rglob("*.py"):
        for name in _imports(path):
            if not name.startswith("app.modules.") or _starts(name, ALLOWED_CROSS_MODULE):
                continue
            other = name.split(".")[2]
            if other != module.name:
                assert name == f"app.modules.{other}.public", f"{path.relative_to(APP_DIR)} imports {name}"


def test_no_imports_from_other_services() -> None:
    for path in APP_DIR.rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, OTHER_SERVICES), f"{path.relative_to(APP_DIR)} imports {name}"
''',
    "tests/architecture/test_access_control.py": r'''"""
Every route carries an operation_id and the central check, and config/access-control.json grants each
one to some role. Runs in a subprocess so it checks the app exactly as it starts.
"""

import subprocess
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[2]


def test_access_control_setup_is_valid() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_access.py"], cwd=SERVICE_DIR, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
''',
}

# Repository-level files (paths relative to the repository root).

REPO_FILES: dict[str, str] = {
    "deploy/db/roles-{{service}}.sql": r'''-- Least-privilege roles for {{service}} (run once per environment as an admin role).
-- Same PostgreSQL server as the identity service, but its own schema: the service can neither read nor change
-- other services' tables. Alembic runs as {{service_snake}}_owner; the API as {{service_snake}}_rw.

CREATE ROLE {{service_snake}}_owner LOGIN PASSWORD :'owner_password';
CREATE ROLE {{service_snake}}_rw LOGIN PASSWORD :'app_password';

GRANT CONNECT ON DATABASE app TO {{service_snake}}_owner, {{service_snake}}_rw;

CREATE SCHEMA IF NOT EXISTS {{service_snake}} AUTHORIZATION {{service_snake}}_owner;
REVOKE ALL ON SCHEMA {{service_snake}} FROM PUBLIC;
GRANT USAGE ON SCHEMA {{service_snake}} TO {{service_snake}}_rw;

ALTER DEFAULT PRIVILEGES FOR ROLE {{service_snake}}_owner IN SCHEMA {{service_snake}}
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {{service_snake}}_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE {{service_snake}}_owner IN SCHEMA {{service_snake}}
  GRANT USAGE, SELECT ON SEQUENCES TO {{service_snake}}_rw;

-- Keep other services' schemas closed to these roles (public is the identity service's schema).
REVOKE ALL ON SCHEMA public FROM {{service_snake}}_owner, {{service_snake}}_rw;

-- Secret keys: DB_USERNAME={{service_snake}}_rw, MIGRATION_DB_USERNAME={{service_snake}}_owner.
''',
    "deploy/helm/domain-service/values-{{service}}.yaml": r'''# {{service}} release:
#   helm upgrade --install {{service}} deploy/helm/domain-service \
#     -f deploy/helm/domain-service/values-{{service}}.yaml --set image.tag=<git-sha>

serviceName: {{service}}

image:
  repository: ghcr.io/your-org/your-repo/{{service}}

config:
  DB_SCHEMA: {{service_snake}}
  PROBLEM_TYPE_BASE_URI: https://errors.example.com
  # Share rate-limit counters across replicas, e.g. redis://redis:6379/2
  RATE_LIMIT_STORAGE_URI: memory://

existingSecret: {{service}}-secrets

networkPolicy:
  allowedCallers: []   # other services' pods (app.kubernetes.io/name) that call this one directly
''',
}

COMPOSE_BLOCK = r'''  # --- {{service}}: an independent domain service (own image, own schema, own migrations) ---
  {{service}}-migrate:
    build:
      context: .
      dockerfile: services/{{service}}/Dockerfile
      args:
        APP_VERSION: ${APP_VERSION:-0.0.0-local}
    command: ["alembic", "upgrade", "head"]
    environment: &{{service}}-env
      ENVIRONMENT: production
      APP_VERSION: ${APP_VERSION:-0.0.0-local}
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: ${DB_NAME:-app}
      # Use a dedicated role in real deployments (see deploy/db/roles-{{service}}.sql); compose shares the app user.
      DB_USERNAME: ${DB_USERNAME:-app}
      DB_PASSWORD: ${DB_PASSWORD:?Set DB_PASSWORD in .env (see .env.example)}
      DB_SCHEMA: {{service_snake}}
      # Verifies the access tokens the identity service issues, so it must equal the identity service's SECRET_KEY.
      JWT_SECRET_KEY: ${SECRET_KEY:?Set SECRET_KEY in .env (see .env.example)}
      PROBLEM_TYPE_BASE_URI: ${PROBLEM_TYPE_BASE_URI:-https://errors.localhost.test}
      CORS_ORIGINS: '["${FRONTEND_URL:-http://localhost:3000}"]'
      RATE_LIMIT_STORAGE_URI: redis://redis:6379/2
    depends_on:
      db:
        condition: service_healthy

  {{service}}:
    build:
      context: .
      dockerfile: services/{{service}}/Dockerfile
      args:
        APP_VERSION: ${APP_VERSION:-0.0.0-local}
    container_name: {{service}}
    environment: *{{service}}-env
    read_only: true
    tmpfs:
      - /tmp
    ports:
      - "{{port}}:8000"
    depends_on:
      {{service}}-migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy

'''

PRECOMMIT_BLOCK = r'''      - id: {{service}}-ruff
        name: ruff ({{service}})
        entry: uv run --directory services/{{service}} task check
        language: system
        types: [python]
        files: ^services/{{service}}/
        pass_filenames: false

      - id: {{service}}-mypy
        name: mypy ({{service}})
        entry: uv run --directory services/{{service}} mypy .
        language: system
        types: [python]
        # platform-kit changes can break the service's types too.
        files: ^(services/{{service}}|packages/platform-kit)/
        pass_filenames: false
        stages: [pre-push]

'''
