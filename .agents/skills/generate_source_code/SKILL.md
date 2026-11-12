---
name: generate-source-code
description: Generates the production code of one build unit (one aggregate) from its spec folder (specs/<service>/<module>/ holding service.yaml, <slug>.rules.yaml and <slug>.domain.yaml) and its failing developer suite, in two phases - `core` (domain, application, infrastructure) then `api` (schemas, router, container, public). Works on that one module only. Use after generate-test-suite (TDD step 2). With --change CHG-<n>, changes only the components and files a Stage 3 change set lists (<slug>.changes.yaml in the same spec folder) until the updated tests are green. Arguments - <spec folder> <phase: core | api> [--change CHG-<n>].
---
# Generate the source code for one build unit

You make the failing developer suite of **one build unit** (one aggregate) pass by writing its code, following the
architecture rules, in **two phases run separately, with a review between them**:

| Phase | Writes | Done when |
| :--- | :--- | :--- |
| `core` | `domain/`, `application/`, `infrastructure/`, the ORM model registration, settings and the migration | domain, policy, use-case and repository tests are GREEN |
| `api` | `schemas.py`, `router.py`, `container.py`, `public.py` and the root wiring (`app/container.py`, `app/api.py`) | the whole developer suite is GREEN, including integration tests; the QA suite passes locally |

The specs and the tests are the specification: **do not change either to make them pass.** The reference
implementation is `services/identity/app/modules/users/`, the only service in the repository. Match its structure,
style, comments and naming.

**Domain events are out of scope at this stage.** Do not create `domain/events.py`, an `EventPublisher` port or
an event adapter. Ignore section F of the domain file, every `emits:`,
and every `after_commit: publish …` step; list what you skipped in the report.

## Run · paste the module's spec folder here

Before each run, paste the path of the spec folder of the **one module** to build, choose the phase, then run
this skill.

```text
SPEC  = specs/<service>/<module>   # e.g. specs/monitoring/accession_management
PHASE = core                       # core first; api after the core phase is reviewed and committed
CHANGE =                           # leave empty; or a change set id such as CHG-1 for a change run
```

- `SPEC` may be relative to the Boost repository root or a full path, with `/` or `\`.
- Values typed after the command (`/generate-source-code <path> <core|api> [--change CHG-<n>]`) override the ones
  above for that run.
- If `SPEC` or `PHASE` is empty and nothing was typed, ask for it and stop.

## Inputs

**Resolve the spec folder first.** `<spec>` is the `SPEC` value above (or the typed path), shaped
`specs/<service>/<module>/`. From that path:

- `<service>` is the folder name after `specs/` (`monitoring`); its code is in `services/<service>/`;
- `<module>` is the next folder name (`accession_management`);
- `<slug>` is the file name before `.rules.yaml` (`accession_management.rules.yaml` → `accession_management`); the
  module package is `services/<service>/app/modules/<slug>/` (normally `<slug>` equals `<module>`);
- the folder must hold exactly one `*.rules.yaml`, the matching `<slug>.domain.yaml` and the module's
  `service.yaml` (and `<slug>.changes.yaml` after a Stage 3 update);
- `service.yaml` is the service description generated for this module: `<spec>/service.yaml` (or `<spec>/<slug>.service.yaml`), in the same folder. Below, `service.yaml` means that file.

```
specs/<service>/
└── <module>/
    ├── service.yaml             (or <slug>.service.yaml)
    ├── <slug>.rules.yaml
    ├── <slug>.domain.yaml
    └── <slug>.changes.yaml      (only after a Stage 3 change)
```

If the path does not have that shape or a file is missing, write the issues file (`blocker`) and stop. Work on this
one build unit only: never read, test or change another module folder under `specs/<service>/`, and never another
module's code.


| Input | Use |
| :--- | :--- |
| `<spec>/<slug>.domain.yaml` | **The design contract:** every class, field, method, exception code, port method, use case, endpoint, table and adapter, and the file each one goes in. |
| `services/<service>/tests/business_rules/*<slug>*` and the fakes | The executable contract: the names the tests import and exactly what each case must prove. |
| `<spec>/<slug>.rules.yaml` | Every rule and case; `status` says what to build, the case `layer` says where the rule is implemented. |
| `<spec>/service.yaml` | Service folder, package, DB schema, API prefix, roles, settings, external systems, scheduled jobs. |
| `qa/<service>-acceptance/tests/test_<slug>_acceptance.py` (`api` phase) | Endpoints, payloads and responses a client relies on. |
| `services/<service>/openapi.json`, if it exists (`api` phase) | Paths, field names (camelCase), status codes already published. |
| `AGENTS.md`, `docs/index.html` (`#entity-vs-service`, `#example`) | Layer rules and where each kind of rule lives. |

Names come from `<slug>.domain.yaml` exactly as spelled there, and they already match what the tests import. If a
test imports a name the domain file does not define (or the reverse), write it to the issues file and stop.

## Architecture rules (the architecture tests enforce most of them)

- `domain/` is plain Python: no FastAPI, Pydantic, SQLAlchemy, `app.core`, `app.config` or other modules. The clock
  and the acting user are passed in.
- `application/` imports only the domain, its own ports, `app.core` / `platform_kit` (errors, config, logging,
  auth) and other modules' `public.py`. Never HTTP schemas, ORM models or infrastructure.
- Ports are ABCs; adapters and fakes inherit them explicitly (`class SqlAlchemySourceRepository(SourceRepository)`).
- Use cases never commit; the request middleware does. Side effects that must follow a commit go in
  `uow.after_commit(...)`.
- Domain exceptions carry a stable `code`; they reach the client as RFC 9457 problem details with the status the
  spec gives. Never raise `HTTPException` outside the router.
- Every endpoint has `rate_limit(...)`, a stable `operation_id`, and passes the central access check
  (`require_access()` on the router); ownership checks stay in the use cases. **No role name appears in code**
  (see "Access control" below).
- Other modules import only `public.py` (re-exports, no logic). Other contexts are reached only by ID or API (port +
  adapter using `ServiceClient`); never read another service's schema.
- UTC, timezone-aware datetimes everywhere.

## Access control (both phases)

Who may call which endpoint is **data**, not code (`docs/adr/0017-central-access-control.md`). The specs still
name roles; this skill turns them into grants in the central access document `config/access-control.json`
(roles → privileges → `(service, operationId)`), never into checks in code.

| Spec says | Becomes |
| :--- | :--- |
| J `api.operations[].operation_id` | `operation_id="<operation_id>"` on the route, spelled exactly as in the spec (camelCase, unique in the service, never renamed) |
| J `api.operations[].roles` | Grants in `config/access-control.json` (API step 1, row 7). The route itself checks nothing: `require_access()` on the router does |
| I `permission.roles` | **Nothing in code.** The endpoint that calls the use case is checked by its `operationId`. A use case without an endpoint (scheduled job, other module through `public.py`) is not access-checked; list it in the report |
| I `permission.admin_allowed: true` | The spec's endpoint grants are also given to the `admin` role in the document |
| I `permission.ownership: owner` | Stays in the use case: load, and raise the module's not-found exception for anyone but the owner (404, no ID probing), like `check_ownership` in `app/modules/auth/dependencies.py` |
| `ownership: owner` **and** `admin_allowed: true` | The "may act on any owner's records" exception is a **declared operation** `actOnAny<Aggregate>` (e.g. `actOnAnySource`), not a role: the router passes `act_on_any=grant.allows("actOnAny<Aggregate>")` (from `grant: AccessGrant = Depends(check_access)`) to the use case, the operation is added to `install_access(..., extra_operations=...)` in the service's app factory, and granted to `admin` in the document |

- Never write `is_admin`, `require_role`, `require_permission`, `Principal.role == …`, a `*_ROLE` constant or a
  permission enum. Copy the access pattern of `services/identity/app/modules/users/router.py`.
- Refusals are the platform's: 401 when the caller is not signed in, 403 `access_denied` when no role holds the
  operation. Do not define module exceptions for them.

## Which rules to build (both phases)

| `status` in rules.yaml / traceability | What to do |
| :--- | :--- |
| `build` | Build every component in its traceability row that belongs to this phase. |
| `pending` | Build only the parts that have cases; leave a `# TODO(<OQ id>)` where the open part would go. |
| `blocked` | Build nothing. List it in the report. |
| `non_code_measure` (classification) | Build nothing; it is measured outside the code. List it in the report. |

## Issues file (both phases)

Whenever this skill must stop, it first writes `issues/<service>/<slug>.generate-source-code.issues.yaml`
(repository root) in the shape of the Stage 3 issues template: `raised_by: generate-source-code`, the phase in
`summary`, one issue per problem with `severity` (`blocker` when a Step 0 check fails, `gap` when the spec leaves
something the code needs), `location` pointing at the spec entry, the `problem`, and a `suggested_fix` that lists
options. The specs are then fixed in the Stage 3 kit, re-validated there and copied again.

## When the spec leaves a gap (both phases)

- A business value, rule, field, format or error code the code needs is `null` or missing in the spec: write a
  `gap` issue and **stop**. Do not invent it, and do not use an open question's `default_assumed` unless the
  spec row itself holds that value.
- A framework mechanic the spec does not size (rate limit, page size, ETag format, timeout): copy what the
  reference module uses for the same kind of operation and list it in the report. This is not a gap.
- A row with `assumption:` passed the Stage 3 review (its `confirm` issue was resolved): build it as written and
  copy the assumption into a one-line comment.
- A conflict with a `default_in_this_spec`: build that default and put the conflict ID in a comment at that place.

If a test looks wrong (it contradicts the specs or cannot pass under the architecture rules), write it to the issues file and stop;
do not edit it silently.

---

## Phase `core` · domain, application, infrastructure

### Core step 0 · Check the starting point

If any of these fails, write the issues file (`blocker`) and **stop**.

1. The test suite exists: `uv run pytest tests/business_rules/test_<slug>_traceability.py -q` passes and
   `uv run pytest tests/business_rules -k <slug> -q` fails (RED).
2. Every BR in `<slug>.rules.yaml` has a `traceability` row in `<slug>.domain.yaml`, and the reverse.
3. Every role and setting the domain file uses exists in `service.yaml`.
4. Every error `code` under `api.operations[].errors` and `use_cases[].errors` is an exception in section G, or a
   framework error the reference service already defines (e.g. the If-Match 412).
5. Every module in this module's `uses_modules` already exists in `services/<service>/app/modules/`.
6. The service is on central access control: `platform_kit.access` exists, the service's app factory
   (`app/main.py`) calls `install_access(...)`, and `config/access-control.json` exists. If not, the blocker is
   "service not on central access control yet (ADR 0017)": do not add role checks as a workaround.

### Core step 1 · Scaffold

- **The service does not exist yet** (`service.yaml` `service.folder`): write a `blocker` issue ("service
  `<service>` does not exist; create it with `python scripts/new_service.py <service>` first") and stop. Do not
  create a service yourself.
- **The service exists:** create `app/modules/<slug>/` by hand with the folders of the reference module
  (`domain/`, `application/ports/`, `application/use_cases/`, `infrastructure/persistence/`, each with an
  `__init__.py`). Do not create `router.py`, `schemas.py`, `container.py` or `public.py` yet.
- **Do not run `scripts/new_module.py`** for a build unit: it also writes a sample router, schemas, container,
  public API and tests, and registers them in `app/container.py` and `app/api.py`. Those belong to the `api` phase,
  and its sample route (`create<Singular>`) is granted to no role, so the access architecture test would fail.
- Leave any module listed in `service.existing_modules_not_in_handover` untouched.

### Core step 2 · Fill the files, inside out

Work layer by layer and run that layer's tests before moving on.

| # | Spec section (`<slug>.domain.yaml`) | File | What goes in it | Done when |
| :--- | :--- | :--- | :--- | :--- |
| 1 | G `exceptions` | `domain/exceptions.py` | Base `<Entity>RuleViolation(Exception)` with `code` and `message`; one subclass per row with its `code`, plain Python like `users/domain/exceptions.py`. The HTTP status in `http` is applied in the use case, as the reference does: catch the violation and raise the `app.core.errors` class with that status (400 `BadRequestError`, 404 `NotFoundError`, 409 `ConflictError`, 412 `PreconditionFailedError`), keeping `code` and `message`. If no class in `app/core/errors.py` has that status, write a blocker issue and stop. | — |
| 2 | C `value_objects` | `domain/value_objects.py` | One self-validating class per row: `kind` (`str` subclass, `enum` with `parse`, frozen dataclass), `constraints`, `trim`; raises the row's `error` | domain value tests pass |
| 3 | C `aggregates` | `domain/entities.py` | `@dataclass(slots=True)` root with `identity`, `fields` (value-object types), `children`; `invariants` in `__post_init__`; `factory` as a `@classmethod` setting `initial_state` and `defaults`; `lifecycle` enum and `transitions`, raising `on_invalid`; one method per `behaviours` row (`params`, `precondition`, `changes`, `errors`); one method per `guards` row (no state change). No event recording. | `test_<slug>_domain.py` passes |
| 4 | D `policies` | `domain/policies.py` | One pure function per row with its `inputs`; facts and `settings` passed in, never fetched | `test_<slug>_policies.py` passes |
| 5 | E `domain_services` | `domain/services.py` | One stateless function or class per row over its `aggregates` (omit the file if the list is empty) | — |
| 6 | H `ports` (except `EventPublisher`) | `application/ports/<port_snake>.py` | `<Port>(ABC)` with exactly the listed `methods` and `signature`s; document `concurrency`, `atomic`, `unique_on` and `raises` in each docstring | the fakes still instantiate |
| 7 | I `use_cases` | `application/use_cases/<file>` (+ `_base.py`, `__init__.py`) | One class per row, a command dataclass from `command`; `steps` in order: `load` → `check` (ownership from `permission` → not-found for strangers unless `act_on_any`; `expected_version` → 412; **never a role**) → `call` (behaviour / policy) → `save` → `in_transaction:` effects inline → `after_commit:` effects (other than publishing events) in `uow.after_commit`; raises the listed `errors` | `test_<slug>_use_cases.py` passes |
| 8 | `service.yaml` `settings` used by this module | `app/core/config.py`, `.env.example` | Each setting with its `type`, `default`, `constraints`; `secret: true` → read from the secrets store, never a literal | — |
| 9 | K `persistence.tables` | `infrastructure/persistence/models.py` + register in `app/models.py` | One model per table in `service.db_schema`: `columns` (type, nullable, default, primary key), `constraints` (check, unique, foreign key **only within this service**), `indexes`; `external_ids` as plain columns, never a foreign key | — |
| 10 | H `ports` + K `atomic_operations` | `infrastructure/persistence/sqlalchemy_<entity>_repository.py` (and one file per other repository port) | Implements the port; explicit row ↔ entity mapping rebuilding value objects; compare-and-set on `version` where `concurrency: compare_and_set_version`; one SQL `UPDATE … RETURNING` per `atomic_operations` row; `IntegrityError` → `ConflictError` | `test_<slug>_repository.py` passes |
| 11 | L `adapters`, `integrations` (except event publishers) | the `file` each row names | One adapter per port; other contexts through `ServiceClient`, external systems through their protocol; secrets only via the secrets-store port | — |

### Core step 3 · Migration

```powershell
cd services/<service>
uv run alembic revision --autogenerate -m "create <slug>"   # then review: tables, constraints, indexes, downgrade
uv run task upgrade
```

Update `docs/DATABASE_DESIGN.md` from section K.

### Core step 4 · Verify

```powershell
cd services/<service>
uv run pytest tests/business_rules/test_<slug>_domain.py tests/business_rules/test_<slug>_policies.py tests/business_rules/test_<slug>_use_cases.py tests/business_rules/test_<slug>_repository.py -q   # GREEN
uv run pytest tests/business_rules/test_<slug>_traceability.py -q                                   # GREEN
uv run pytest tests/architecture -q
uv run task format; uv run task check; uv run task type-check
git diff --stat -- tests/business_rules ../../specs    # must be empty
```

`test_<slug>_integration.py` is still expected to FAIL: there is no router yet. Omit any test file that does not
exist (the spec had no case for that layer).

### Core step 5 · Report

1. Files created or changed, grouped by layer (domain, application, infrastructure, config, migration).
2. Where each rule lives so far: `BR-xx → components → files`, checked against `traceability` (flag differences).
3. Rules not built: `blocked`, `non_code_measure`, the open parts of `pending` rules (with OQ IDs), and every
   event, `emits:` and publish step skipped.
4. Framework values copied from the reference (rate limits, page size …), and the issues file if one was written.
5. Migration summary.
6. Test results of every command in core step 4, including the expected integration failures.
7. Tests or spec entries you believe are wrong, with the reason (unchanged).

Stop here. Commit the core layers (for example `feat(<slug>): domain, application and infrastructure`) and run the
`api` phase after review.

---

## Phase `api` · schemas, router, container, public

### API step 0 · Check the starting point

If any of these fails, write the issues file (`blocker`) and **stop**.

1. The `core` phase is done: the domain, policy, use-case and repository tests of `<slug>` pass.
2. `app/modules/<slug>/` has no `router.py`, `schemas.py`, `container.py` or `public.py` yet (or only the ones a
   previous `api` run left; then continue from there).
3. Every role in section J `roles` and section I `permission` exists in `service.yaml` `auth.roles`.
4. Every operation in section J has an `operation_id` (camelCase), unique within the service, and none is already
   used by another route of the service or granted under another module's privilege in `config/access-control.json`.
5. Core step 0 check 6 (central access control installed) still holds.

Do not change the `domain/`, `application/` or `infrastructure/` files in this phase. If an endpoint cannot be
built without changing them, write it to the issues file and stop.

### API step 1 · Fill the files

| # | Spec section | File | What goes in it | Done when |
| :--- | :--- | :--- | :--- | :--- |
| 1 | J `api.schemas` | `schemas.py` | Pydantic request/response models with camelCase aliases as in `json`; `from_entity` mapping like the reference; never a field listed in `excluded`; validates shape only, rules stay in the domain | — |
| 2 | H `ports`, L `adapters`, I `use_cases` | `container.py` | Providers for every port's adapter (except event publishers) and every use case; dependencies (`db`, `uow`, clock, other modules' public use cases) injected from the root container | — |
| 3 | J `api.operations` | `router.py` | `APIRouter(prefix=…, tags=[…], dependencies=[require_access()])` with `prefix` = `api.base_path` without the leading `service.api_prefix` (`/v1/sources` → `/sources`), so the mounted path is exactly `api.base_path`; one thin route per operation: `method` + `path`, `operation_id=` from the spec, `rate_limit`, the caller resolved for the use case (`CurrentUserDep` from `app/modules/auth/dependencies.py`), **no role check**, `act_on_any=grant.allows(…)` only where "Access control" says so, `If-Match` → `expected_version` and `ETag` / `Location` as in `headers_in` / `headers_out`, one use-case call, `response.status`; list operations use `list.filters` (allow-list) and paginate with the repository's page-size limit | — |
| 4 | top-level `public_api` | `public.py` | Re-exports of exactly those use cases (and the entity / value objects they return); no logic | — |
| 5 | `service.yaml` `scheduled_jobs` | `app/worker.py` (ARQ) | Each job wired to its `use_case` and `schedule_setting`; a job calls the use case in-process (not access-checked; list it in the report). No role names anywhere: `app/modules/auth/dependencies.py` only resolves the caller (`roles_of`) | — |
| 6 | — | `app/container.py`, `app/api.py`, app factory | Register the module container and mount the router under `service.api_prefix`; add any `actOnAny<Aggregate>` to `install_access(..., extra_operations=...)` | app starts (startup validates the access setup) |
| 7 | J `roles`, I `admin_allowed` | `config/access-control.json` | One privilege per role of this module, key `<slugCamel><RolePascal>` (e.g. `sourceRegisterProductionOps`), `name` "<module title> · <role>", `endpoints: {"<service>": [the operationIds whose `roles` list that role]}`; add the key to `roles.<role>` (create the role with that one privilege if it is new). `admin_allowed: true` → also a privilege `<slugCamel>Admin` with those operations (plus `actOnAny<Aggregate>`) for `roles.admin`. Change no other module's privileges | every operationId of section J is granted to its spec roles |

### API step 2 · Contract and documentation

```powershell
cd services/<service>
uv run task openapi                                          # compare with section J of <slug>.domain.yaml
```

- The exported `openapi.json` must show exactly the paths, statuses, fields and error codes in section J.
- Update `docs/API_FLOW.md` from section J.
- If the web app uses the endpoints: `pnpm gen:api` in `web/`.

### API step 3 · Verify

```powershell
cd services/<service>
uv run task test-br                         # every developer case GREEN, including integration; traceability GREEN
uv run pytest tests/architecture -q         # includes the access check: operation_id + require_access on every route
uv run task format; uv run task check; uv run task type-check
uv run task test                            # whole suite: nothing else broke
git diff --stat -- tests/business_rules ../../specs app/modules/<slug>/domain app/modules/<slug>/application app/modules/<slug>/infrastructure   # must be empty
git grep -nE "is_admin|require_role|require_permission|_ROLE\b|\.role ==" -- app/modules/<slug>   # must be empty
```

Then run the QA suite against a local server (`RATE_LIMIT_ENABLED=false`, seeded):
`cd qa/<service>-acceptance; uv run task test`.

### API step 4 · Report

1. Files created or changed (HTTP boundary, wiring).
2. Where each rule lives now: `BR-xx → components → files`, complete, checked against `traceability`.
3. Endpoints: method, path, `operationId`, status, error codes, rate limit (and which rate limits were copied
   from the reference).
4. Access: the privileges added to `config/access-control.json` (`privilege → roles → operationIds`), any declared
   `actOnAny<Aggregate>` operation, and every use case with `permission.roles` that has no endpoint (not checked).
5. The OpenAPI changes (new paths, `operationId`s, fields, statuses), and any difference from section J.
6. Test results of every command in API step 3 and of the QA suite, including any failure output.
7. Tests or spec entries you believe are wrong, with the reason (unchanged).

---

## Change mode · `--change CHG-<n>` (a business rule changed after the code was written)

The build unit's code exists and was green before the change. Stage 3 changed only some rules and recorded
exactly what in `<spec>/<slug>.changes.yaml`, change set `CHG-<n>`; `generate-test-suite --change CHG-<n>`
has already updated the tests, and only those tests are RED. Make them green by changing **only what the change
set lists**, in the phase you were asked for.

### Change step 0 · Check

If any fails, write the issues file (`blocker`) and stop.

1. Change set `CHG-<n>` exists with `handed_off: false`, and the test suite has been updated for it: the
   traceability tests pass and the failing business-rule tests are only those of the cases the change set adds or
   updates.
2. `core` phase: everything the change set lists outside `schemas.py`, `router.py`, `container.py`, `public.py`.
   `api` phase: only when `handoff.api_contract` is true, and the `core` change is done (its tests green).
3. Every component the change set lists exists in `<slug>.domain.yaml` (or, if removed, no longer does), and every
   file in `handoff.code_files` exists in the module (or is a file the change set adds).

### Change step 1 · Change the code

- Work through `components` (`changed`, `added`, `removed`) in the order of the Core / API step tables: exceptions,
  value objects, entity, policies, ports, use cases, persistence, adapters, then schemas, router, container,
  public. Change each to match its section in the new `<slug>.domain.yaml`; nothing else in the file changes.
- Touch only the files in `handoff.code_files`, plus the wiring a new port, use case or adapter needs. A file
  outside that list that must change is a `gap` issue: write it and stop.
- `handoff.migration: true`: create a new migration for exactly the section K difference
  (`uv run alembic revision --autogenerate -m "<slug>: CHG-<n>"`); never edit an existing migration. Review its
  `upgrade` and `downgrade`, and how existing rows are handled (a new not-null column needs a default or a
  backfill; say which in the report). Update `docs/DATABASE_DESIGN.md`.
- `handoff.api_contract: true` (`api` phase): change only the listed operations and schemas, run
  `uv run task openapi`, and update `docs/API_FLOW.md`. A removed or renamed field, path or status is a breaking
  change: list it in the report. An `operation_id` is never renamed; a new operation gets its grants in
  `config/access-control.json`, a removed one is taken out of this module's privileges, and changed `roles`
  change only this module's privileges (API step 1, row 7).
- The rules in "When the spec leaves a gap" apply unchanged.

### Change step 2 · Verify and report

```powershell
cd services/<service>
uv run task test-br                         # the whole developer suite GREEN, not only the changed cases
uv run pytest tests/architecture -q
uv run task format; uv run task check; uv run task type-check
git diff --stat -- tests/business_rules ../../specs   # must be empty
git diff --stat                                       # only the files the change set lists, wiring and migration
```

Then the QA suite against a local server when the change set lists acceptance cases.

Report: the change set id; a table `component → file → what changed`; files changed outside `handoff.code_files`
(should be none, or the wiring); the migration and how it treats existing rows; OpenAPI and breaking changes; test
results of every command; issues. Commit (for example `feat(<slug>): CHG-<n> <rule ids>`), then set
`handed_off: true` on the change set in the Stage 3 kit.
