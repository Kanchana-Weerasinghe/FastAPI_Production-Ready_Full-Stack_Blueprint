---
name: generate-source-code
description: Generates the production code of one entity from its test catalogue (specs/<service>/<entities>.rules.yaml), the failing developer suite and the business-rule documents, filling every layer folder and file by the architecture rules. Use after generate-test-suite (TDD step 2). Arguments - <service> <entities> [business-rules file] [test-case file].
---
# Generate the source code for an entity

You make the failing developer suite of **one entity** pass by writing its code in every layer, following the
architecture rules. The tests and the catalogue are the specification: **do not change them to make them pass.**
The reference implementation is `services/identity/app/modules/users/` (identity modules) or
`services/data-acquisition/app/modules/acquisition_jobs/` (domain services). Match their structure, style,
comments and naming.

## Inputs

Arguments: `<service> <entities> [business-rules file] [test-case file]`, for example `identity projects`.

| Input | Use |
| :--- | :--- |
| `specs/<service>/<entities>.rules.yaml` | Every rule and case; the layer tells you where the rule is implemented. |
| `services/<service>/tests/business_rules/*<entities>*` and `tests/mocks/<entity>_repository.py` | The design contract: module paths, class, method and exception names, error codes, statuses. |
| `qa/<service>-acceptance/tests/test_<entities>_acceptance.py` | Endpoints, payloads and responses a client relies on. |
| `services/<service>/openapi.json` or the agreed OpenAPI draft | Paths, field names (camelCase), status codes. |
| Business-rule and test-case documents | Wording and intent when a test leaves a detail open. |
| `AGENTS.md`, `docs/index.html` (`#entity-vs-service`, `#example`, `#service-files`) | Layer rules and where each kind of rule lives. |

## Architecture rules (the architecture tests enforce most of them)

- `domain/` is plain Python: no FastAPI, Pydantic, SQLAlchemy, `app.core` or other modules. The clock is passed in.
- `application/` imports only the domain, its own ports, `app.core` (errors, config, logging) and other modules'
  `public.py`. Never HTTP schemas, ORM models or infrastructure.
- Ports are ABCs; adapters and fakes inherit them explicitly (`class SqlAlchemyProjectRepository(ProjectRepository)`).
- Use cases never commit; the request middleware does. Side effects that must follow a commit go in
  `uow.after_commit(...)`.
- Domain exceptions carry a stable `code`; use cases translate them to `app.core.errors` (e.g. `BadRequestError`).
  Never raise `HTTPException` outside the router.
- Every endpoint has `@rate_limit(...)` / `dependencies=[rate_limit(...)]`, authentication via `CurrentUserDep`,
  and ownership or permission checks (`check_ownership`, `require_permission`).
- Other modules import only `public.py` (re-exports, no logic).
- UTC, timezone-aware datetimes everywhere.

## Step 1 · Scaffold

- **Identity module:** from `services/identity/` run `uv run python scripts/new_module.py <entities>`
  (`--singular <entity>` if needed). It creates the layers, registers the model in `app/models.py`, the container in
  `app/container.py` and the router in `app/api.py`.
  Then **replace the sample**: it ships an example "name" rule, `application/use_cases/create.py` and sample tests
  in `tests/unit/modules/<entities>/`. Keep only what the spec asks for; rename files to the names the tests import
  (e.g. `application/use_cases/<entity>_use_cases.py`); delete the sample tests the business-rule suite replaces.
- **Domain service aggregate:** copy the folder layout of `acquisition_jobs` and wire it in the service's
  `app/container.py`, `app/api.py` (or `main.py`) and model registry the same way.

## Step 2 · Fill every file, inside out

Work layer by layer and run that layer's tests before moving on.

| # | File | What goes in it | Done when |
| :--- | :--- | :--- | :--- |
| 1 | `domain/exceptions.py` | Base `<Entity>RuleViolation(Exception)` with `code` and `message`; one subclass per broken rule, `code` as the tests expect | — |
| 2 | `domain/value_objects.py` | One self-validating value per validated concept (str subclass or frozen dataclass); raises a domain exception | domain tests for values pass |
| 3 | `domain/entities.py` | `@dataclass(slots=True)` entity built from value objects; invariants in `__post_init__`; behaviours named as business verbs that check guards, change state and raise domain exceptions | `test_<entities>_domain.py` passes |
| 4 | `domain/policies.py` | Pure functions for decisions that need facts the entity does not hold (config, clock, counts) | `test_<entities>_policies.py` passes |
| 5 | `domain/events.py` | Domain services only: events the behaviours record | — |
| 6 | `application/ports/<entity>_repository.py` | `<Entity>Repository(ABC)` with exactly the methods the use cases and the fake use | fake still instantiates |
| 7 | `application/use_cases/<entity>_use_cases.py` | `<Entity>UseCases`: load → let the entity decide → persist the change; translate domain errors; register after-commit effects | `test_<entities>_use_cases.py` passes |
| 8 | `infrastructure/persistence/models.py` | SQLAlchemy model: columns, nullability, lengths, unique constraints and indexes the rules require | — |
| 9 | `infrastructure/persistence/sqlalchemy_<entity>_repository.py` | Implements the port; explicit row ↔ entity mapping; atomic SQL `UPDATE` where a rule must hold under concurrency; translate `IntegrityError` to `ConflictError` | `test_<entities>_repository.py` passes |
| 10 | `infrastructure/<technology>_<port>.py` | Any other adapter (event publisher, HTTP client) | — |
| 11 | `schemas.py` | Pydantic request/response models, camelCase aliases like the users schemas; no secrets in responses | — |
| 12 | `router.py` | Thin routes: validate, authenticate, authorise, call the use case via `Provide["<entities>.use_cases"]`, map to a response; statuses as the spec says | `test_<entities>_integration.py` passes |
| 13 | `container.py` | Providers for the repository, use cases and adapters; dependencies injected from the root container | app starts |
| 14 | `public.py` | Re-exports other modules may use | architecture tests pass |
| 15 | `app/container.py`, `app/api.py`, `app/models.py` | Review the scaffold's wiring; pass `uow`, `storage`, `audit_service` etc. that the container needs | app starts |

If a test looks wrong (it contradicts the documents or cannot pass under the architecture rules), stop and report
it; do not edit it silently.

## Step 3 · Database, contract and documentation

```powershell
cd services/<service>
uv run alembic revision --autogenerate -m "create <entities>"   # then review the file: constraints, indexes, downgrade
uv run task upgrade
uv run task openapi                                              # compare with the agreed contract
```

- Update `docs/DATABASE_DESIGN.md` (tables, columns, constraints) and `docs/API_FLOW.md` (endpoints, statuses,
  error codes) with the documentation skill.
- If the web app uses the endpoints: `pnpm gen:api` in `web/`.

## Step 4 · Verify

```powershell
cd services/<service>
uv run task test-br                         # every developer case GREEN, traceability GREEN
uv run pytest tests/architecture -q
uv run task format; uv run task check; uv run task type-check
uv run task test                            # whole suite: nothing else broke
git diff --stat -- tests/business_rules ../../specs   # must be empty
```

Then run the QA suite against a local server (`RATE_LIMIT_ENABLED=false`, seeded):
`cd qa/<service>-acceptance; uv run task test`.

## Step 5 · Report

1. Files created or changed, grouped by layer.
2. Where each rule lives: `BR-xx → value object / behaviour / policy / use case / repository / router`.
3. Migration summary and the OpenAPI changes (new paths, fields, statuses).
4. Test results of every command in step 4, including any failure output.
5. Tests or spec entries you believe are wrong, with the reason (unchanged).
