# Onboarding: productive on day one

## 1. Tools

Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm 10, Docker Desktop (tests start Postgres in a container), an editor with the recommended extensions (`.vscode/extensions.json`).

## 2. Run it

```bash
git clone <repo> && cd <repo>
uvx pre-commit install --hook-type pre-commit --hook-type pre-push

# Backend: Postgres via Docker, then migrations, demo data, dev server on :8000
docker run -d --name dev-db -e POSTGRES_USER=root -e POSTGRES_PASSWORD=password -e POSTGRES_DB=postgres -p 5432:5432 postgres:16-alpine
cd services/core-api && uv sync && uv run task upgrade && uv run task seed && uv run task dev

# Frontend on :3000
cd ../../web && pnpm install && pnpm dev
```

Sign in with `demo@example.com` / `Password123!` (or `admin@example.com` for admin endpoints). API docs: http://localhost:8000/docs. Emails are delivered inline in development (no worker needed); set `AUTOSEND_API_KEY` to send real ones.

Everything at once, production-like: `cp .env.example .env` (fill secrets) and `docker compose up --build`.

## 3. Understand it (reading order, ~1 hour)

1. [README.md](../README.md) and [AGENTS.md](../AGENTS.md): structure and commands.
2. [ADR index](adr/README.md): 0001 (modular monolith), 0002 (errors), 0004 (unit of work), 0008 (sessions).
3. Read the [request lifecycle diagram](../AGENTS.md#backend-request-lifecycle) and [module creation guide](../AGENTS.md#creating-a-backend-module), then trace `services/core-api/app/modules/todos/` (router → application use case → domain/ports → infrastructure adapter) and its tests.
4. [docs/API_FLOW.md](API_FLOW.md) and [docs/DATABASE_DESIGN.md](DATABASE_DESIGN.md).
5. Operations: [deployment](operations/deployment.md), [SLOs](operations/slo.md), [runbooks](operations/runbooks/).

## 4. First change

- Add a module: `uv run python scripts/new_module.py projects`, then follow the step-by-step walkthrough in the [developer guide](../AGENTS.md#creating-a-backend-module). Review the migration, add domain/application/integration tests, and open a PR using the template.
- Checks run on commit (pre-commit) and in CI; `uv run task test` and `pnpm test` locally.

## 5. Access to request

GitHub team, Sentry project, log platform, staging cluster (read-only), cloud console (SSO). See [access control](governance/access-control.md).
