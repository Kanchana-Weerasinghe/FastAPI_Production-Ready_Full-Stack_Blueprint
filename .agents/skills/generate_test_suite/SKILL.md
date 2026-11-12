---
name: generate-test-suite
description: Generates the developer test suite and the QA acceptance suite for one build unit (one aggregate) from its spec folder - specs/<service>/<module>/ holding service.yaml, <slug>.rules.yaml and <slug>.domain.yaml. Works on that one module only. Use before any production code exists (TDD step 1); run generate-source-code afterwards. With --change CHG-<n>, updates only the tests of the cases a Stage 3 change set lists (<slug>.changes.yaml in the same spec folder). Arguments - <spec folder> [--change CHG-<n>].
---
# Generate the test suite for one build unit from its specs

You turn the Stage 3 specs of **one build unit** (one aggregate) into:

1. the developer suite in `services/<service>/tests/business_rules/`,
2. the QA acceptance suite in `qa/<service>-acceptance/`.

The test catalogue already exists: it is `<spec>/<slug>.rules.yaml`. **Do not create, edit or reformat
it.** You write **tests only**. Never write or change production code under `services/<service>/app/`.
The reference for every test file below is the `UserAccount` entity (`users`) of the identity service: copy its
structure, style and naming exactly. The *code names* the tests import come from `<slug>.domain.yaml` (one class per use case).

## Run · paste the module's spec folder here

Before each run, paste the path of the spec folder of the **one module** to test, then run this skill.

```text
SPEC   = specs/<service>/<module>        # e.g. specs/monitoring/accession_management
CHANGE =                                 # leave empty; or a change set id such as CHG-1 for a change run
```

- `SPEC` may be relative to the Boost repository root or a full path, with `/` or `\`.
- A path typed after the command (`/generate-test-suite <path> [--change CHG-<n>]`) overrides `SPEC` for that run.
- If `SPEC` is empty and no path was typed, ask for it and stop.

## Inputs

**Resolve the spec folder first.** `<spec>` is the `SPEC` value above (or the typed path), shaped
`specs/<service>/<module>/`. From that path:

- `<service>` is the folder name after `specs/` (`monitoring`); its code is in `services/<service>/`;
- `<module>` is the next folder name (`accession_management`);
- `<slug>` is the file name before `.rules.yaml` (`accession_management.rules.yaml` → `accession_management`); it is
  the module package `services/<service>/app/modules/<slug>/` and normally equals `<module>`;
- the folder holds exactly one `*.rules.yaml`, the matching `<slug>.domain.yaml` and the module's `service.yaml`
  (and, in a change run, `<slug>.changes.yaml`);
- `service.yaml` is the service description generated for this module: `<spec>/service.yaml` (or `<spec>/<slug>.service.yaml`), in the same folder. Below, `service.yaml` means that file.

```
specs/<service>/
└── <module>/
    ├── service.yaml             (or <slug>.service.yaml)
    ├── <slug>.rules.yaml
    ├── <slug>.domain.yaml
    └── <slug>.changes.yaml      (only after a Stage 3 change)
```

If the path does not have that shape, `services/<service>/` does not exist (create it with
`python scripts/new_service.py <service>`), or a file is missing, write the issues file (`blocker`) and stop. Work
on this one build unit only: never read, test or change another module folder under `specs/<service>/`, and never
another module's code.


| Input | Use |
| :--- | :--- |
| `<spec>/<slug>.rules.yaml` | Source of truth for rule and case IDs, wording, Given / When / Then and each case's `layer`. |
| `<spec>/<slug>.domain.yaml` | **The design contract the tests import:** module path, class, method, field, exception and code names, port methods, use cases, endpoints, statuses, response fields. |
| `<spec>/service.yaml` | Service folder, API prefix, roles (validation and QA test users), settings (for values a test needs). |
| `services/<service>/openapi.json`, if it exists | Paths and fields already published. Missing ones come from section J of the domain file. |
| `AGENTS.md`, `docs/index.html` (`#entity-vs-service`, `#tdd`) | Architecture, layer rules, naming. |

Read first: `specs/identity/users.rules.yaml`, every file in `services/identity/tests/business_rules/`,
`services/identity/tests/mocks/` and `qa/identity-acceptance/` (README, `tests/`).

## Rules

- **Never invent rules, cases or names.** Rule and case IDs and wording come from `<slug>.rules.yaml`; every class,
  method, exception code, path and field a test uses comes from `<slug>.domain.yaml`, spelled the same. If a case
  names something the domain file does not define, or a case is ambiguous, add it to
  `issues/<service>/<slug>.generate-test-suite.issues.yaml` (`severity: gap`) and write no test for that case; do
  not fill the gap.
- IDs are used exactly as the spec writes them (`BR-MON-1.0`, `TC-MON-1.0-1`). Do not convert them to `BR-<n>`.
- **One test per case**, tagged `@pytest.mark.br("<rule id>", "<case id>")`, named
  `test_<rule id lowercased, "-" and "." → "_">_<what it proves>`, e.g. `test_br_mon_1_0_unknown_source_type_is_rejected`.
  Parametrize inside one test when a case's `given` lists alternatives (`a / b`).
- Each test asserts exactly the case's **Then**: the exception and its `code`, the HTTP status and problem `code`,
  what is saved and what is not, what runs only after commit.
- Timestamps are timezone-aware UTC; the clock is passed in (`at=NOW`), never read inside the domain.
- Which rules get tests:

| `status` in rules.yaml | Tests |
| :--- | :--- |
| `build` | One test per case. |
| `pending` | One test per case that exists (only the agreed parts have cases). |
| `blocked` | None (the rule has no cases). |

### Access control in tests

Who may call an endpoint is data in `config/access-control.json`, checked once by `require_access()` on the
router (`docs/adr/0017-central-access-control.md`). Tests prove the **check applies to the endpoint's
`operationId`**, not that a role name is compared in code:

| A case proves | Layer | How the test does it |
| :--- | :--- | :--- |
| A role may call an endpoint | `integration` | `grant_access("<operationId>")`, sign in, call → the success status |
| Another role / a caller without the grant is refused | `integration` | `grant_access(<the other operationIds>)` or `deny_access()`, sign in, call → **403**, problem `code` `access_denied` |
| Not signed in | `integration` | no sign-in → **401** |
| Only the owner may see / act (strangers get 404) | `use_case` and `integration` | ownership stays in the use case: a stranger's call raises the module's not-found exception (404 over HTTP), with the operation granted |
| Admins may act on any owner's records (`ownership: owner`, `admin_allowed: true`) | `use_case` | call the use case with `act_on_any=True` (allowed) and without it (not found); over HTTP grant `actOnAny<Aggregate>` together with the operation |
| Acceptance: a role may / may not call | `acceptance` | sign in as a QA user who holds that role in the environment's access document (Step 3) |

- `grant_access(*operation_ids)` / `deny_access()` are the fixtures in `services/<service>/tests/conftest.py`; they
  replace the access document, never the check. Use the `operation_id` values of section J exactly.
- Never build a test user from a role to prove access (`auth(role=...)`, `Role.ADMIN`, a role claim) and never
  assert a `forbidden` code: refusals are `access_denied`.
- A `use_case` case whose Then is "refused because of the caller's role" cannot be proved there any more (use
  cases do not check roles): write no test, and add a `gap` issue suggesting the case move to `integration`.

## Step 0 · Check the specs

If any of these fails, write `issues/<service>/<slug>.generate-test-suite.issues.yaml` (repository root) in the
shape of the Stage 3 issues template — `raised_by: generate-test-suite`, one issue per failure with
`severity: blocker`, `location` pointing at the spec entry, the `problem`, and a `suggested_fix` that lists
options — then **stop**. Do not fix the specs yourself and do not write any test: the specs are fixed in the
Stage 3 kit, re-validated there and copied again.

1. `<slug>` is in `service.yaml` `modules` (directly or under a module's `aggregates:`) with `status` `build` or
   `pending`.
2. Every case has exactly the keys `id`, `layer`, `given`, `when`, `then`, and `layer` is one of `domain`,
   `use_case`, `repository`, `integration`, `acceptance`.
3. Every name a case uses in `when` / `then` exists in `<slug>.domain.yaml` with the same spelling.
4. Every error `code` a case expects is an exception in section G, or a framework error the reference service
   already defines (e.g. the If-Match 412).
5. Every role a case needs exists in `service.yaml` `auth.roles`.
6. Every operation in section J has an `operation_id` (camelCase, unique in the service).
7. The service is on central access control: `platform_kit.access` exists and `services/<service>/tests/conftest.py`
   provides `grant_access` and `deny_access`. If not, the blocker is "service not on central access control yet
   (ADR 0017)": do not fall back to role-based test users.

## Step 1 · Map the design contract

Before writing tests, list the names the tests will import, all taken from `<slug>.domain.yaml`:

| Tests import | From section | Module path (`app/modules/<slug>/…`) |
| :--- | :--- | :--- |
| Exceptions and their `code` | G `exceptions` | `domain/exceptions.py` |
| Value objects (`parse`, constructor) | C `value_objects` | `domain/value_objects.py` |
| Aggregate root, factory, behaviours, guards, lifecycle enum | C `aggregates` | `domain/entities.py` |
| Policy functions | D `policies` | `domain/policies.py` |
| Domain services | E `domain_services` | `domain/services.py` |
| Port ABCs and their methods (except `EventPublisher`) | H `ports` | `application/ports/<port_snake>.py` |
| Use-case classes and command dataclasses | I `use_cases` | `application/use_cases/<file>` (exported from `__init__.py`) |
| SQLAlchemy adapter | L `adapters` | the `file` each row names |
| Endpoints, statuses, JSON fields | J `api` | `<api.base_path><path>` (`base_path` already includes `service.api_prefix`, e.g. `POST /v1/sources/`) |
| `operationId` of each endpoint (for `grant_access`) | J `api.operations[].operation_id` | `operation_id=` on the route |
| `act_on_any: bool = False` keyword on a use case's `execute` | I `permission`: `ownership: owner` and `admin_allowed: true` | `application/use_cases/<file>`; declared operation `actOnAny<Aggregate>` |

This list goes into the report unchanged; `generate-source-code` must produce exactly these names.

**Domain events are out of scope at this stage.** Ignore section F, every `emits:` and every
`after_commit: publish …` step: no test asserts that an event is recorded or published, and no fake publisher is
written. If a case's `then` can only be proved by an event, list it under "Questions".

## Step 2 · The developer suite (`services/<service>/tests/business_rules/`)

Create the folder with `__init__.py` and a `conftest.py` that registers the `br` marker if they do not exist.

| File | Contents | Copy from |
| :--- | :--- | :--- |
| `<slug>_catalogue.py` | Loader of `<spec>/<slug>.rules.yaml` (`SPEC_PATH`, `DEV_LAYERS`, `ALL_LAYERS`, `<SLUG>_RULES`). Reads only `id`, `rule`, `visibility` and `cases`; ignores the other rule keys. | `users_catalogue.py` |
| `<slug>_builders.py` | `NOW`, `a_<entity>(**overrides)` returning a valid aggregate built through its factory, recording fakes, a `UseCaseWorld` holding every use case of section I wired to the fakes | `users_builders.py` |
| `test_<slug>_domain.py` | `domain` cases about value objects, invariants, behaviours, guards, lifecycle | `test_users_domain.py` |
| `test_<slug>_policies.py` | `domain` cases whose `when` names a function in section D | `test_users_policies.py` |
| `test_<slug>_use_cases.py` | `use_case` cases with the `world` fixture and in-memory fakes; `in_transaction` effects asserted before commit, `after_commit` effects only after `uow.commit()` | `test_users_use_cases.py` |
| `test_<slug>_repository.py` | `repository` cases with `db_session` and the SQLAlchemy adapter of section L | `test_users_repository.py` |
| `test_<slug>_integration.py` | `integration` cases with `client()` / `isolated_app_transaction`; access with `grant_access` / `deny_access` ("Access control in tests") | `test_users_integration.py`, `tests/integrations/test_access_control.py` |
| `test_<slug>_traceability.py` | Every developer case in the spec has exactly one test; every tag points to a developer case (glob `test_<slug>_*.py`) | `test_users_traceability.py` |
| Fakes (`tests/fakes.py` or `tests/mocks/<port_snake>.py`, where the reference keeps them) | `Fake<Port>(<Port>)` for every port in section H except `EventPublisher`, in memory, with only its listed methods; honour `concurrency: compare_and_set_version` and `raises` | `tests/mocks/user_repository.py` |

Add a `world` fixture for the build unit to `conftest.py` (name it `<slug>_world` if `world` is taken).
Omit a file when the spec has no case for its layer.

## Step 3 · The QA acceptance suite (`qa/<service>-acceptance/`)

If the project does not exist, create it as a copy of `qa/identity-acceptance/` (pyproject, `tests/support/`,
`conftest.py`, `test_traceability.py`, README) with the service's URL and OpenAPI path.

Create `tests/test_<slug>_acceptance.py`, one test per `acceptance` case:

- Black box only: `ApiSession` and user fixtures. No imports from `services/`, no database, no mail.
- A case that needs a role from `service.yaml` (e.g. `production_ops`) uses a fixture that signs in a QA user
  holding that role in the environment (credentials from settings, like `QA_ADMIN_EMAIL`), so the environment's
  access document decides; refusals are asserted as 403 `access_denied`. If the QA project has no such user,
  add the fixture as a stub that skips with the reason, and list it under "Questions". (A fixture that grants
  given `operationId`s through an admin API comes with the access tables; until then there is none.)
- Each test creates its own data through the API, so it can run against any environment.
- Call `contract.check(response, METHOD, PATH)` on every response the case is about.
- If an endpoint is not in `openapi.json` yet, use the path from section J of the domain file and list it under
  "Contract to add" in the report.

## Step 4 · Verify

```powershell
cd services/<service>; uv run pytest tests/business_rules/test_<slug>_traceability.py -q   # must PASS
cd services/<service>; uv run pytest tests/business_rules -k <slug> -q                     # must FAIL (RED): no code yet
cd qa/<service>-acceptance; uv run pytest tests/test_traceability.py -q                    # must PASS
cd qa/<service>-acceptance; uv run task check; uv run task type-check
cd services/<service>; uv run task check
git diff --stat -- specs                                                                 # must be empty
```

Import errors in the developer suite are the expected RED state. Lint must pass.

## Step 5 · Report

End with a report the developer reviews:

1. Counts: rules by status, cases per layer, tests per file.
2. The design contract the tests import (the Step 1 list). Flag any name a test needs that the domain file lacks.
3. Contract to add: endpoints or fields from section J missing from `openapi.json`.
4. Acceptance cases that need a role or fixture the QA project does not have yet.
5. Access: `operationId` → spec roles for every endpoint (what `generate-source-code` must grant in
   `config/access-control.json`), and any `use_case` role case moved to an issue.
6. Issues: the path of the issues file and a table `ID → severity → location → problem`, or "none".

Commit the tests (for example `test(<slug>): add the business-rule suite`) before running `generate-source-code`,
so its diff shows only code.

---

## Change mode · `--change CHG-<n>` (a business rule changed after the suite was written)

The build unit already has its tests (and usually its code). Stage 3 changed only some rules and recorded exactly
what in `<spec>/<slug>.changes.yaml`, change set `CHG-<n>`. Update **only those tests**; every other test
stays byte for byte as it is.

### Change step 0 · Check

Run Step 0 above on the new specs, plus these. If any fails, write the issues file (`blocker`) and stop.

1. `<spec>/<slug>.changes.yaml` has a change set `CHG-<n>` with `handed_off: false`.
2. Every case id in its `handoff.tests.add` and `update` exists in `<slug>.rules.yaml`; every id in `delete` does
   not (it is in the rule's `retired_cases`, or its rule was removed).
3. The existing suite matches the previous specs: `uv run pytest tests/business_rules/test_<slug>_traceability.py -q`
   fails **only** on the case ids the change set adds or deletes (and the QA traceability test likewise).

### Change step 1 · Update the tests

| Change set lists | Do |
| :--- | :--- |
| `tests.add` | Write one new test per case, in the file its `layer` belongs to (Step 2 / Step 3 tables), tagged and named as above |
| `tests.update` | Rewrite the test tagged with that case id so it asserts the new Then; keep its tag; rename it only if `what it proves` changed |
| `tests.delete` | Delete the test tagged with that case id |
| `components` added / changed / removed | Update only the builders, fakes and imports those tests need (e.g. a new port method on the fake) |

Do not touch any other test, even one in the same file. If a listed change would break a test of an unchanged
case, do not edit that test: write it to the issues file (`gap`) and stop.

### Change step 2 · Verify and report

```powershell
cd services/<service>; uv run pytest tests/business_rules/test_<slug>_traceability.py -q   # PASS again
cd services/<service>; uv run pytest tests/business_rules -k <slug> -q                     # only the changed / added cases FAIL (RED)
cd qa/<service>-acceptance; uv run pytest tests/test_traceability.py -q                    # PASS
git diff --stat                                                                            # only test files, builders and fakes
```

Report: the change set id; a table `case id → added / updated / deleted → test name → file`; the RED tests; any
builder or fake changed; issues. Commit (for example `test(<slug>): CHG-<n> <rule ids>`) before running
`/generate-source-code <spec> core --change CHG-<n>`.
