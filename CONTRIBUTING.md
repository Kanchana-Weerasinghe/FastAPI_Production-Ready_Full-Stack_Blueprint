# Contributing

## Workflow

- **Trunk-based**: short-lived branches off `main` (`feat/…`, `fix/…`), merged within days via pull request. Large features ship incrementally behind a feature flag.
- `main` is protected: pull request required, at least one approving review (plus CODEOWNERS for owned paths), all CI checks green, linear history (squash merge), no force pushes.
- **Conventional Commits** for PR titles (`feat:`, `fix:`, `perf:`, `docs:`, `chore:`, `feat!:` for breaking): release-please derives versions and the changelog from them.
- Fill in the pull request checklist; reviewers check it.

## Local setup (day one)

See [docs/onboarding.md](docs/onboarding.md). In short:

```bash
uvx pre-commit install --hook-type pre-commit --hook-type pre-push
cd server && uv sync && uv run task upgrade && uv run task seed && uv run task dev
cd web && pnpm install && pnpm dev
```

## Conventions

- Backend architecture and rules: [AGENTS.md](AGENTS.md), ADRs in [docs/adr](docs/adr). New domain → `uv run python scripts/new_module.py <name>`.
- Errors: raise domain errors from `app/core/errors.py`; never `HTTPException` in services.
- Every API change updates `server/openapi.json` (`uv run task openapi`), the generated web types (`pnpm gen:api`) and `docs/API_FLOW.md`.
- Every schema change ships a reviewed, backward-compatible migration ([docs/database/migrations.md](docs/database/migrations.md)) and updates `docs/DATABASE_DESIGN.md`.
- Tests: unit tests for services, integration tests for endpoints (real Postgres via testcontainers); coverage must stay ≥ 90%.
