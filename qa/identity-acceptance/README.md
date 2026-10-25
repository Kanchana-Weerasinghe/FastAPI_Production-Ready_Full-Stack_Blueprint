# Identity acceptance suite (QA-owned)

Black-box tests for the identity service. They use only the public HTTP API and the published
OpenAPI contract (`services/identity/openapi.json`). They never import service code or touch the database.

| | Developer suite | This suite |
| :--- | :--- | :--- |
| Location | `services/identity/tests/business_rules/` | `qa/identity-acceptance/` |
| Owner | Developers | QA team |
| Spec layers | `domain`, `use_case`, `repository`, `integration` | `acceptance` |
| Sees | Code, fakes, database | HTTP API + OpenAPI only |
| Runs against | Testcontainers (in-process) | Any running environment (local, QA, staging) |

Both suites read the same specs: `specs/identity/<entity>.rules.yaml`. Every `acceptance` case in a spec must have
exactly one test in `tests/test_<entity>_acceptance.py` (e.g. `users.rules.yaml` → `test_users_acceptance.py`),
tagged `@pytest.mark.br("BR-xx", "TC-xx-y")`. `tests/test_traceability.py` checks this.

## Run

```powershell
uv sync
uv run task test                              # against http://localhost:8000
$env:QA_BASE_URL = "https://identity.qa.example.com"; uv run task test
uv run pytest tests/test_traceability.py      # spec coverage only, no service needed
```

The target environment must run identity with `RATE_LIMIT_ENABLED=false` (the suite signs up and signs in many
times) and have a seeded admin account.

| Variable | Default |
| :--- | :--- |
| `QA_BASE_URL` | `http://localhost:8000` |
| `QA_ADMIN_EMAIL` / `QA_ADMIN_PASSWORD` | `admin@example.com` / `Password123!` (from `uv run task seed`) |
| `QA_LOGIN_MAX_FAILED_ATTEMPTS` | `5` (must match the service's `LOGIN_MAX_FAILED_ATTEMPTS`) |
| `QA_OPENAPI` | `services/identity/openapi.json` |
| `QA_SPEC_DIR` | `specs/identity` (every `<entity>.rules.yaml` in it) |

## Contract check

`Contract.check(response, method, path)` asserts that success responses use a documented status and match
the OpenAPI schema, and that error responses are RFC 9457 Problem Details with a stable `code`.
The OpenAPI document does not yet list error responses (only success and 422), so error bodies are checked
for shape, not against the contract.
