# Agent & Project Guidelines

Welcome! This document provides commands, rules, and guidelines for developing and managing the Tempto project.

---

## Agent Behavior Rules

> These rules take highest priority and must be followed at all times.

- **Keep responses short** — Always give the smallest response possible unless the user explicitly asks to describe in detail (e.g., "explain", "describe", "in detail").
- **No code changes on questions** — If the user says "tell me", "how", asks a question with "?", or uses similar inquiry language, only answer — do not modify any code or files.
- **Explain differences with tables** — Whenever explaining a difference or comparison between two or more things, always use a markdown table.

---

## 🚀 Quick Commands

### Frontend (`web/`)

* **Install:** `pnpm install`
* **Development Server:** `pnpm dev`
* **Production Build:** `pnpm build`
* **Preview Build:** `pnpm preview`
* **Linting:** `pnpm lint`
* **Lint & Fix:** `pnpm lint:fix`
* **Formatting:** `pnpm format`
* **Format Check:** `pnpm format:check`
* **Unit Testing (watch):** `pnpm test`
* **Unit Testing (UI):** `pnpm test:ui`
* **Unit Testing (coverage):** `pnpm test:cov`
* **E2E Testing:** `pnpm test:e2e`

### Repository layout

| Path | What it is |
| :--- | :--- |
| `services/core-api/` | Identity (auth, users), audit and the `todos` example; issues the access tokens |
| `services/data-acquisition-api/` | Data acquisition domain service (`AcquisitionJob`), deployed independently |
| `packages/platform-kit/` | Shared technical building blocks for domain services (no business rules) |
| `web/` | React front end |
| `deploy/helm/app`, `deploy/helm/domain-service` | Helm charts: core-api + web, and one release per domain service |

Run each service's commands from its own folder. See `docs/adr/0016-independent-domain-services.md`.

### Domain services (`services/<name>-api/`, e.g. `data-acquisition-api`)

* **Environment Sync:** `uv sync` (installs `platform-kit` as an editable path dependency)
* **Development Server:** `uv run task dev` (data-acquisition-api on `:8010`)
* **Migrations:** `uv run task upgrade` (own schema, e.g. `data_acquisition`)
* **Checks:** `uv run task check`, `uv run task format`, `uv run task type-check`
* **Testing:** `uv run task test` (unit, architecture and Testcontainers integration tests)
* **Export OpenAPI contract:** `uv run task openapi` (commit the service's `openapi.json`)
* **Image:** `docker build -f services/<name>-api/Dockerfile .` from the repository root

### Shared package (`packages/platform-kit/`)

* `uv sync`, `uv run task check`, `uv run task type-check`, `uv run task test`. Changes affect every domain service: run their tests too.

### Backend (`services/core-api/`)

* **Environment Sync:** `uv sync`
* **Development Server:** `uv run task dev`
* **Background Worker:** `uv run task worker` (ARQ; needs `REDIS_URL`. Not needed for local dev: outbox events are delivered inline)
* **New Module:** `uv run python scripts/new_module.py <plural_name>` (layered domain/application/ports/infrastructure scaffold)
* **Seed dev data:** `uv run task seed` (development only)
* **Export OpenAPI contract:** `uv run task openapi` (commit `services/core-api/openapi.json`; then `pnpm gen:api` in `web/`)
* **Run Linter:** `uv run task check`
* **Run Formatter:** `uv run task format`
* **Type Checking:** `uv run task type-check`
* **Database Migrations:**
  * **Upgrade:** `uv run task upgrade` (runs `alembic upgrade head`)
  * **Downgrade:** `uv run task downgrade` (runs `alembic downgrade -1`)
* **Testing:** `uv run task test`
* **Generate Coverage HTML Report:** `uv run task cov-html` (runs `pytest --cov=app --cov-report=html`)

---

### Backend Folder Structure (`services/core-api/`)

The application resides in the `services/core-api/app/` directory and is a **modular monolith** (see `docs/adr/0001-modular-monolith.md`):

* `modules/<name>/`: One package per business domain, organized into `domain/`, `application/ports/`, `application/use_cases/`, `infrastructure/persistence/`, HTTP `router.py`/`schemas.py`, and a DI `container.py`. Create modules with `uv run python scripts/new_module.py <plural_name>`.
  * `domain/` contains persistence- and framework-independent entities, value objects, policies, and domain exceptions.
  * `application/` coordinates use cases and defines ports. It must not import HTTP schemas, web frameworks, ORM models, or infrastructure adapters.
  * `infrastructure/persistence/` implements application ports and maps between domain records and SQLAlchemy models.
  * The root `service.py` is the module's public application API for routes and other modules; keep it to re-exports, not business logic. Put use-case implementations under `application/use_cases/`.
  * `router.py` and `schemas.py` translate and validate HTTP input/output; keep business rules in the domain and application layers.
  * Cross-module workflows use another module's public service/application API. Do not import another module's repository, infrastructure, router, or container. Keep domain entities module-local; use application contracts for cross-module data.
  * `auth/dependencies.py` provides `CurrentUserDep` and `check_ownership(...)` for route authentication and resource ownership checks.

* `shared/`: Base model/repository/service, pagination schemas (`schemas.py`), file storage, the `Actor` protocol, outbound integrations (`integrations/`) and utilities.

* `core/`: Config, database + `UnitOfWork` (`database.py`), domain errors (`errors.py`) and RFC 9457 handlers (`error_handlers.py`), security, logging, middleware, client IP resolution. Imports nothing from `shared`/`modules`.

* `container.py` / `api.py` / `models.py`: Composition root (DI wiring), router registry per API version (`/v1`, `/v2`), and model registry for Alembic.

### Domain Service Structure (`services/<name>-api/`)

Same layering as core-api modules, but the service *is* the bounded context and its modules are its aggregates (e.g. `app/modules/acquisition_jobs/`):

* `domain/`: `entities.py` (aggregate with behaviour methods and domain events), `value_objects.py`, `policies.py`, `events.py`, `exceptions.py` (extend `platform_kit.errors`). Plain Python: no FastAPI, Pydantic, SQLAlchemy or `app.config`.
* `application/ports/` (`Protocol` interfaces) and `application/use_cases/` (one class per use case; receives a `Principal` and transport-neutral values). May import only `platform_kit.errors` and `platform_kit.auth` from platform-kit.
* `infrastructure/`: SQLAlchemy models (the service's schema via `app/db.py`), repository adapter, event publisher adapter, HTTP clients to other services.
* `router.py`, `schemas.py`, `container.py`, `service.py` as in core-api; `app/auth.py` resolves the caller from the bearer token.
* Never import another service's code or read another service's schema; reference other aggregates by ID, call their API through a port, or consume their events. `tests/architecture/test_layers.py` enforces the layer rules.

### Frontend Folder Structure (`web/`)

The source code resides in the `web/src/` directory:

* `components/`: Reusable component library. Shared/atomic inputs are placed in `common/` (e.g. `Button.tsx`, `Input.tsx`, `Modal.tsx`).

* `constants/`: Shared UI and navigation configuration constants.

* `features/`: Modular components implementing feature-specific pages (e.g., `todo/TodoList.tsx`, `todo/TodoEdit.tsx`, `Archives.tsx`).

* `hooks/`: React state and fetching hooks:
  * `queries/`: React Query hooks for fetching data (e.g., `todos.ts`).
  * `mutations/`: React Query mutations for sending data (e.g., `auth.ts`, `todos.ts`).
  * `shared/`: Generic frontend helpers (e.g., `useDebounce.ts`).

* `lib/`: Client utilities such as the API axios `client.ts` and query configuration `query.ts`.

* `models/`: Client-side Zod validation schemas and types (e.g., `todo.ts`).

* `routes/`: File-based TanStack Router configuration directories (e.g., `_authenticated/`, `_guest/`).

* `store/`: Client-side state stores (e.g. `auth.store.ts`).

* `utils/`: Formatting and processing helper functions (e.g. `helper.ts`).

---

### Backend Technology Stack

* **FastAPI (Async)** for the API layer.
* **SQLAlchemy 2.0 (Async)** with `asyncpg` for database connection and ORM.
* **Dependency Injector** for IoC container management.
* **Alembic** for schema migrations.
* **Layered modular architecture**: HTTP routes -> application use cases/services -> domain rules and application ports -> infrastructure adapters -> SQLAlchemy models and database.

### Frontend Technology Stack

* **React 19 (TypeScript)** built with **Vite 8**.
* **React Compiler (babel-plugin-react-compiler)**: Memoization is automatic. Avoid manual `useMemo` and `useCallback` unless necessary.
* **TanStack Router**: File-based routing with automatic code-splitting enabled in `vite.config.ts`.
* **TanStack Query & Form**: Server state caching and type-safe form validations.
* **Zod**: Validation schemas aligned with backend Pydantic models.

---

## 📖 Coding & Design Guidelines

### Frontend

- **Routing & Code Splitting**:
   * Keep page-specific components inside the `web/src/features/` directory.
   * Map them to files in `web/src/routes/` using static route configurations. The build pipeline handles code splitting automatically.
- **Search Components**:
   * When searching within a paginated view, always reset the current page parameter to `1` on query changes (`setPage(1)`) to avoid out-of-bounds pagination matches.
- For writing tests for the frontend, follow the `react-testing` skill.

### Backend

- **Async flow**: Use `async`/`await` for database operations and other asynchronous I/O.
- **Rate limiting**: Apply the existing `@rate_limit` decorator to API endpoints according to their resource profile.
- **UTC datetimes**: Save and process timestamps as timezone-aware UTC values.
- **Transactions**: The request middleware owns the transaction. Application services and repositories must not commit. Register side effects that must only happen after a successful commit with `uow.after_commit(...)`.
- **Errors**: Raise framework-agnostic application/domain errors from `app/core/errors.py`; the HTTP exception handlers convert them to RFC 9457 responses. Do not raise `HTTPException` from application or persistence code.
- **Tests**: For backend tests, follow the `python-testing` skill and the existing unit, architecture, and integration test patterns.

### Backend Request Lifecycle

The diagram below follows a typical authenticated write request. Optional idempotency handling runs outside the request transaction for supported methods when the client supplies an `Idempotency-Key`.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Idem as Idempotency middleware
    participant Core as Core middleware
    participant Router as FastAPI router
    participant Handler as RFC 9457 exception handlers
    participant Auth as Auth and ownership dependencies
    participant App as Application use case/service
    participant Domain as Domain entity and policy
    participant Port as Application repository port
    participant Adapter as SQLAlchemy repository adapter
    participant DB as PostgreSQL

    Client->>Idem: HTTP request
    opt POST/PATCH with Idempotency-Key
        Idem->>DB: Claim key in separate short transaction
        DB-->>Idem: New key, replay, or conflict
    end
    Idem->>Core: Forward request
    Core->>Core: Validate request size; bind request ID and log context
    Core->>DB: Open request-scoped session and transaction
    Core->>Router: Dispatch request
    Router->>Router: Validate path, query, and body with FastAPI/Pydantic
    Router->>Auth: Resolve authenticated user and resource ownership
    Auth->>DB: Read identity/resource through its application service
    DB-->>Auth: Domain/application record
    Auth-->>Router: Authorized request context
    Router->>App: Call use case with validated transport-neutral values
    App->>Domain: Apply entity invariants and business policies
    Domain-->>App: Valid domain state or rule violation
    App->>Port: Request persistence operation
    Port->>Adapter: Runtime adapter implements the port
    Adapter->>DB: Query, insert, update, or delete using ORM models
    DB-->>Adapter: Persisted model/result
    Adapter-->>App: Map ORM state to domain/application record
    App-->>Router: Return result
    Router->>Router: Serialize successful response
    Router-->>Core: HTTP response
    alt Successful response (status below 400)
        Core->>DB: Commit request transaction
        opt Registered after-commit callbacks
            Core->>App: Run callbacks after response body is sent
        end
        Core-->>Idem: Return response with X-Request-ID
        opt Idempotency key was claimed
            Idem->>DB: Store response for safe replay
        end
        Idem-->>Client: Return successful response
    else Error response (status 400 or above)
        Router->>Handler: Translate validation, application, or unexpected error
        Handler-->>Core: RFC 9457 Problem Details response
        Core->>DB: Roll back request transaction and discard callbacks
        Core-->>Idem: Return error with X-Request-ID
        Idem-->>Client: Return error response
    end
```

**Important transaction behavior:**

- A successful request commits once at the middleware boundary; services and repositories never commit.
- Error responses roll back writes and discard after-commit callbacks. A small number of security bookkeeping flows may explicitly request persistence on failure through `UnitOfWork.persist_on_failure()`.
- After-commit callbacks run only after a successful commit and after the response body is sent. A callback failure is logged and cannot undo the committed transaction.
- The idempotency record uses its own short transaction and is stored only after the inner request transaction has completed; server errors are not cached.

### Creating a Backend Module

Start from the layered scaffold, then adapt its example business rule rather than treating the generated sample as a complete feature.

- **Generate the module** from the `services/core-api/` directory:

  ```powershell
  uv run python scripts/new_module.py projects
  ```

  The optional `--singular` argument overrides automatic singularization, for example `uv run python scripts/new_module.py news --singular news_item`. The generator creates the module and unit-test folders and adds its ORM model, DI container, and router to the composition root.

- **Define domain concepts** in `app/modules/<name>/domain/`. Put entity identity and behavior in `entities.py`, validated values in `value_objects.py`, business decisions in `policies.py`, and domain-specific violations in `exceptions.py`. Keep this layer independent of FastAPI, Pydantic, SQLAlchemy, and other modules.

- **Define application contracts and use cases** in `application/ports/` and `application/use_cases/`. Use cases coordinate domain rules and persistence through a `Protocol` port; they should receive transport-neutral values and return domain/application records.

- **Implement persistence** in `infrastructure/persistence/`. Define SQLAlchemy models in `models.py`; implement the repository port in `repository.py`; map ORM models to and from domain entities explicitly.

- **Finish the HTTP boundary** in `schemas.py` and `router.py`. Validate request/response shapes there, resolve authentication and ownership with the existing auth dependencies, call the use case through dependency injection, and map the returned entity to a response schema.

- **Wire dependencies** in the module `container.py`. The generator registers the module in `app/container.py`, registers the ORM model in `app/models.py`, and mounts the router in `app/api.py`; review those generated changes and add explicit providers for cross-module services or external adapters as needed.

- **Add behavior-focused tests** for domain invariants and policies, application use cases with fake ports, repository mapping/queries, and API integration behavior where appropriate. Run focused tests first, then the relevant architecture checks.

- **Create and review the migration** after model changes:

  ```powershell
  uv run alembic revision --autogenerate -m "create projects"
  uv run task upgrade
  ```

  Review the generated migration before applying it; autogeneration does not replace migration review. Update `docs/DATABASE_DESIGN.md` for schema changes and `docs/API_FLOW.md` for API contract changes.

- **Run checks** from `services/core-api/` before opening a pull request:

  ```powershell
  uv run task check
  uv run task type-check
  uv run pytest tests/unit/modules/projects tests/architecture -q
  ```

  Run integration tests and the broader suite when the change affects route behavior, shared infrastructure, or database integration.

## STRICTLY FOLLOW THESE RULES

- Run `uv run task check`, `uv run task format`, and `uv run task type-check` if **more than 5** `*.py` files in the backend (`services/core-api/app`) codebase have been changed in the current session.
- Run `uv run task cov-html` or `uv run task test` if changes have been made to `*.py` files in the backend (`services/core-api/`) codebase inside the `tests` directory.
- Run `pnpm lint`, `pnpm lint:fix`, `pnpm format`, and `pnpm format:check` if **more than 10** `*.ts` or `*.tsx` files in `web/src/` have been changed in the current session.
- Run `pnpm test` or `pnpm test:cov` if changes have been made to files in the `web/tests/` directory and **more than 5** files have changed in the current session.
- Always update `docs/API_FLOW.md` when making changes to the backend API using the documentation skills.
- Always update `docs/DATABASE_DESIGN.md` when making changes to the database schema using the documentation skills.
