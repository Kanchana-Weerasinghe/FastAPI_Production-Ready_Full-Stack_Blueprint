---
name: generate-test-suite
description: Generates the test catalogue (specs/<service>/<entities>.rules.yaml), the developer test suite and the QA acceptance suite for one entity from the business-rule and test-case documents. Use before any production code exists (TDD step 1). Arguments - <service> <entities> <business-rules file> <test-case file> [OpenAPI draft].
---
# Generate the test suite for an entity

You turn the business rules and test cases of **one entity** into:

1. the test catalogue `specs/<service>/<entities>.rules.yaml`,
2. the developer suite in `services/<service>/tests/business_rules/`,
3. the QA acceptance suite in `qa/<service>-acceptance/`.

You write **tests only**. Never write or change production code under `services/<service>/app/`.
The reference for every file below is the `UserAccount` entity (`users`) of the identity service: copy its
structure, style and naming exactly.

## Inputs

Arguments: `<service> <entities> <business-rules file> <test-case file> [OpenAPI draft]`,
for example `identity projects docs-in/projects-br.xlsx docs-in/projects-test-cases.docx`.

| Input | Use |
| :--- | :--- |
| Business-rules file | Source of truth for rule IDs and wording. |
| Test-case file | Source of truth for test-case IDs, Given / When / Then. |
| `services/<service>/openapi.json` or the OpenAPI draft | Paths, request and response fields for acceptance and integration tests. |
| `AGENTS.md`, `docs/index.html` (`#entity-vs-service`, `#tdd`) | Architecture, layer rules, naming. |

Read first: `specs/identity/users.rules.yaml`, every file in `services/identity/tests/business_rules/`,
`services/identity/tests/mocks/user_repository.py`, and `qa/identity-acceptance/` (README, `tests/`).

## Rules

- **Never invent rules or cases.** Copy rule and case IDs and wording from the documents. If a rule has no case,
  or a case is ambiguous, list it under "Questions" in the report; do not fill the gap yourself.
- IDs: rules `BR-<n>`, cases `TC-<n>-<m>` where `<n>` is the rule number (the spec check enforces the prefix).
  If the documents use another format, stop and ask before converting.
- **One test per case**, tagged `@pytest.mark.br("BR-xx", "TC-xx-y")`, named `test_br_xx_<what_it_proves>`.
  Parametrize inside one test when a case lists several inputs.
- Each test asserts exactly the case's **Then**: the exception and its `code`, the HTTP status and problem `code`,
  what is saved and what is not.
- Timestamps are timezone-aware UTC; the clock is passed in (`at=NOW`), never read inside the domain.

## Step 1 · The test catalogue

Create `specs/<service>/<entities>.rules.yaml` with the same keys as `users.rules.yaml`:
`entity`, `service`, `layers` (copy the block unchanged), `rules[]` → `id`, `rule`, `visibility`, `cases[]` →
`id`, `layer`, `given`, `when`, `then`.

Choose each case's `layer` with this table (the cheapest layer that can prove it):

| The case proves … | Layer | Owner |
| :--- | :--- | :--- |
| A value is valid or invalid; an entity method changes state or refuses to | `domain` | Developers |
| A decision that needs config or the clock (duration, limit, eligibility) | `domain` (policy) | Developers |
| Order of steps, what is saved, error translation, side effects after commit | `use_case` | Developers |
| Row ↔ entity mapping, a database constraint, an atomic SQL update | `repository` | Developers |
| Behaviour through HTTP that needs the database or captured e-mail to set up or check | `integration` | Developers |
| Behaviour a client can see through the published API alone | `acceptance` | QA |

`visibility`: `api` (only acceptance/integration cases), `internal` (no acceptance case), `both`.

## Step 2 · The developer suite (`services/<service>/tests/business_rules/`)

Create the folder with `__init__.py` and a `conftest.py` that registers the `br` marker if they do not exist.

| File | Contents | Copy from |
| :--- | :--- | :--- |
| `<entities>_catalogue.py` | Loader of the YAML (`SPEC_PATH`, `DEV_LAYERS`, `ALL_LAYERS`, `<ENTITIES>_RULES`) | `users_catalogue.py` |
| `<entities>_builders.py` | `NOW`, `a_<entity>(**overrides)` returning a valid entity, recording fakes, a `UseCaseWorld` | `users_builders.py` |
| `test_<entities>_domain.py` | `domain` cases: value objects, invariants, behaviours, guards | `test_users_domain.py` |
| `test_<entities>_policies.py` | `domain` cases that test a policy function | `test_users_policies.py` |
| `test_<entities>_use_cases.py` | `use_case` cases with the `world` fixture and in-memory fakes | `test_users_use_cases.py` |
| `test_<entities>_repository.py` | `repository` cases with `db_session` and `SqlAlchemy<Entity>Repository` | `test_users_repository.py` |
| `test_<entities>_integration.py` | `integration` cases with `client()` / `isolated_app_transaction` | `test_users_integration.py` |
| `test_<entities>_traceability.py` | Spec ↔ tests check for this entity (glob `test_<entities>_*.py`) | `test_users_traceability.py` |
| `tests/mocks/<entity>_repository.py` | `Fake<Entity>Repository(<Entity>Repository)`, in memory | `tests/mocks/user_repository.py` |

Add a `world` fixture for the entity to `conftest.py` (name it `<entity>_world` if `world` is taken).
Omit a file when the spec has no case for its layer.

The tests **fix the design contract** that the code must satisfy. Name things as the domain discovery and the
`#entity-vs-service` guide say:

- modules: `app/modules/<entities>/domain/{entities,value_objects,policies,exceptions}.py`,
  `application/ports/<entity>_repository.py`, `application/use_cases/<entity>_use_cases.py`,
  `infrastructure/persistence/{models,sqlalchemy_<entity>_repository}.py`;
- classes: `<Entity>` entity, value objects named for the concept (`ProjectName`), exceptions `<Rule>`
  with a stable snake_case `code`, `<Entity>UseCases`, `<Entity>Repository(ABC)`, `SqlAlchemy<Entity>Repository`;
- error codes and HTTP statuses exactly as the test-case document says.

## Step 3 · The QA acceptance suite (`qa/<service>-acceptance/`)

If the project does not exist, create it as a copy of `qa/identity-acceptance/` (pyproject, `tests/support/`,
`conftest.py`, `test_traceability.py`, README) with the service's URL and OpenAPI path.

Create `tests/test_<entities>_acceptance.py`, one test per `acceptance` case:

- Black box only: `ApiSession`, `new_user`, `admin` fixtures. No imports from `services/`, no database, no mail.
- Each test creates its own data through the API, so it can run against any environment.
- Call `contract.check(response, METHOD, PATH)` on every response the case is about.
- If an endpoint is not in `openapi.json` yet, use the path from the test-case document or OpenAPI draft and list
  it under "Contract to add" in the report.

## Step 4 · Verify

```powershell
cd services/<service>; uv run pytest tests/business_rules/test_<entities>_traceability.py -q   # must PASS
cd services/<service>; uv run pytest tests/business_rules -k <entities> -q                     # must FAIL (RED): no code yet
cd qa/<service>-acceptance; uv run pytest tests/test_traceability.py -q                        # must PASS
cd qa/<service>-acceptance; uv run task check; uv run task type-check
cd services/<service>; uv run task check
```

Import errors in the developer suite are the expected RED state. Lint must pass.

## Step 5 · Report

End with a report the developer reviews:

1. Counts: rules, cases per layer, tests per file.
2. A table `case → layer → reason` for every case whose layer was a judgement call.
3. The design contract the tests assume: entity, value objects, exceptions + codes, policies, port methods,
   use-case methods, endpoints + statuses.
4. Contract to add: endpoints or fields missing from `openapi.json`.
5. Questions: gaps and ambiguities in the documents.
