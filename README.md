# Boost

**Boost** is a production-ready starter template for building business applications with **FastAPI** and
**React**. It gives every team the same foundation: domain-driven design (entities, value objects, policies,
use cases, ports and adapters), independently deployable domain services, secure authentication, RFC 9457
errors, migrations, observability, CI and Kubernetes deployment, so you can start on business features on day one.

New entities are built test-first from business rules: a rule catalogue (`specs/`) drives a developer test suite
and a QA acceptance suite, and the code is written (or generated with Claude) until both pass. The `User` entity is
the complete reference example.

| Part | What it is |
| :--- | :--- |
| [`services/identity/`](services/identity) | Sign-up, sign-in, sessions, MFA, users, roles and audit log; issues the access tokens |
| [`services/data-acquisition/`](services/data-acquisition) | Example of an independent domain service with its own schema |
| [`packages/platform-kit/`](packages/platform-kit) | Shared technical building blocks for domain services |
| [`web/`](web) | React 19 + TypeScript front end (Vite, TanStack Router / Query / Form) |
| [`specs/`](specs), [`qa/`](qa) | Business-rule catalogues and the QA-owned acceptance suites |
| [`deploy/`](deploy) | Helm charts and Terraform |

📖 **Read the [Boost Guide](docs/index.html)** for the architecture, the delivery process and step-by-step
instructions. It is also served by the running web app at <http://localhost:3000/guide/index.html>.

## Prerequisites

Install these once on your machine:

| Tool | Version | Install |
| :--- | :--- | :--- |
| [Git](https://git-scm.com/downloads) | any | Installer from the website |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` · macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Python](https://www.python.org/) | 3.12 | Nothing to do: `uv` downloads it automatically (each project has a `.python-version`) |
| [Node.js](https://nodejs.org/) | 22.12 or newer (LTS) | Installer from the website |
| [pnpm](https://pnpm.io/) | 10.34.8 (pinned in `web/package.json`) | `corepack enable` (ships with Node.js; run the terminal as administrator on Windows), or `npm install -g pnpm@10.34.8` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | latest | Installer from the website; must be running for the database and the backend tests |

> **Windows:** enable long file paths before cloning and clone into a short folder (for example `C:\dev\boost`).
> Some package paths are deep, and Windows refuses paths longer than 260 characters:
>
> ```powershell
> git config --global core.longpaths true
> ```

## Clone and install all packages

```bash
git clone https://github.com/Kanchana-Weerasinghe/FastAPI_Production-Ready_Full-Stack_Blueprint.git boost
cd boost
```

Install the packages of every project (each `uv sync` creates that project's `.venv` from its `uv.lock`;
`pnpm install` uses `web/pnpm-lock.yaml` without changing it):

```bash
cd services/identity          && uv sync && cd ../..   # identity API (auth, users, audit)
cd services/data-acquisition  && uv sync && cd ../..   # example domain service
cd packages/platform-kit      && uv sync && cd ../..   # shared building blocks for domain services
cd qa/identity-acceptance     && uv sync && cd ../..   # QA acceptance suite
cd web && pnpm install --frozen-lockfile && cd ..      # React front end
```

For day-to-day work on the identity API and the web app, the first and last lines are enough.

Optional extras:

```bash
cd web && pnpm exec playwright install && cd ..        # browsers for the end-to-end tests (pnpm test:e2e)
uvx pre-commit install --hook-type pre-commit --hook-type pre-push   # lint, format and secret scan on every commit
```

## Run locally

```bash
# 1. Start PostgreSQL (first time; afterwards just: docker start dev-db)
docker run -d --name dev-db -e POSTGRES_USER=root -e POSTGRES_PASSWORD=password -e POSTGRES_DB=postgres -p 5432:5432 postgres:16-alpine

# 2. Create the tables and the demo accounts
cd services/identity
uv run task upgrade
uv run task seed

# 3. Start the API (http://localhost:8000, Swagger UI at /docs)
uv run task dev

# 4. In a second terminal, start the web app (http://localhost:3000)
cd web
pnpm dev
```

Sign in with `demo@example.com` or `admin@example.com`, password `Password123!`.

No `.env` file is needed for local development: every setting has a safe development default
(see `services/identity/.env.example` to override one). The data-acquisition service runs the same way from its
own folder (`uv run task upgrade`, then `uv run task dev` on port 8010).

On Windows, set `PYTHONUTF8=1` before `uv run task dev` if the console shows a Unicode error
(PowerShell: `$env:PYTHONUTF8 = "1"`).

### Or run everything with Docker Compose

Copy `.env.example` to `.env`, fill in the secrets, then run `docker compose up --build`
(API on port 8000, web app on port 3000, production settings).

## Check your setup

```bash
cd services/identity && uv run task test     # backend tests (Docker must be running)
cd web && pnpm test --run                     # front-end unit tests
cd web && pnpm build                          # production build of the front end
```

If all three succeed, your machine is ready for development.

## Next steps

- **Build your first entity:** follow the [Quick start](docs/index.html#quick-start) in the Boost Guide.
- **Commands and coding rules:** [`AGENTS.md`](AGENTS.md).
- **Working with Claude:** the `generate-test-suite` and `generate-source-code` skills in [`.agents/skills/`](.agents/skills).
- **Decisions:** the Architecture Decision Records in [`docs/adr/`](docs/adr).

## License

See [LICENSE](LICENSE).
