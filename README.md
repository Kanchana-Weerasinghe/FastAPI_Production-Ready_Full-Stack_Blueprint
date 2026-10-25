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

| Tool | Version |
| :--- | :--- |
| [Git](https://git-scm.com/) | any |
| [Python](https://www.python.org/) | 3.12+ |
| [uv](https://docs.astral.sh/uv/) | latest |
| [Node.js](https://nodejs.org/) | 22.12+ (includes Corepack for pnpm) |
| [Docker](https://www.docker.com/) | for PostgreSQL and the backend tests |

## Clone and install

```bash
git clone https://github.com/Kanchana-Weerasinghe/FastAPI_Production-Ready_Full-Stack_Blueprint.git boost
cd boost

# Backend packages
cd services/identity
uv sync
cd ../..

# Front-end packages
cd web
corepack enable
pnpm install --frozen-lockfile
cd ..
```

## Run locally

```bash
# 1. Start PostgreSQL
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

On Windows, set `PYTHONUTF8=1` before `uv run task dev` if the console shows a Unicode error.

### Or run everything with Docker Compose

Copy `.env.example` to `.env`, fill in the secrets, then run `docker compose up --build`
(API on port 8000, web app on port 3000, production settings).

## Check your setup

```bash
cd services/identity && uv run task test   # backend tests (Docker must be running)
cd web && pnpm test                         # front-end unit tests
```

## Next steps

- **Build your first entity:** follow the [Quick start](docs/index.html#quick-start) in the Boost Guide.
- **Commands and coding rules:** [`AGENTS.md`](AGENTS.md).
- **Working with Claude:** the `generate-test-suite` and `generate-source-code` skills in [`.agents/skills/`](.agents/skills).
- **Decisions:** the Architecture Decision Records in [`docs/adr/`](docs/adr).

## License

See [LICENSE](LICENSE).
