# 🚀Full-Stack Clean Architecture: Production Best Practices with ⚡FastAPI, ⚛️React, and 🐘PostgreSQL

This repository is an example of how to set up a clean full-stack architecture using **⚛️React + TypeScript** for the frontend, **⚡FastAPI** for the backend, and **🐘PostgreSQL** for the database. It serves as a high-performance, production-ready template that combines the speed of modern frameworks with a robust, scalable architecture.

## Table of Contents

- [Configured for Any Agentic IDE you like](#configured-for-any-agentic-ide-you-like)
- [What is Clean Architecture?](#what-is-clean-architecture)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [File Structure](#file-structure)
- [Getting Started](#getting-started)
- [Debugging](#debugging)
- [Bonus - What you can learn](#bonus---what-you-can-learn)
- [Have Improvements or Questions?](#have-improvements-or-questions)
- [Note](#note)

## Configured for Any Agentic IDE you like

<a href="https://antigravity.google/"><img height="48" width="48" style="vertical-align: middle;" src="https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/antigravity-color.svg" /></a>&nbsp;&nbsp;&nbsp;
<a href="https://cursor.com/"><img height="48" width="48" style="vertical-align: middle;" src="https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/cursor.svg" /></a>&nbsp;&nbsp;&nbsp;
<a href="https://claude.ai/"><img height="48" width="48" style="vertical-align: middle;" src="https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/claude-color.svg" /></a>&nbsp;&nbsp;&nbsp;
<a href="https://chatgpt.com/codex"><img height="48" width="48" style="vertical-align: middle;" src="https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/codex-color.svg" /></a>
<br>
This project is configured to work seamlessly with modern AI-powered coding assistants:

- **ANTIGRAVITY**: Supported natively via the `.agents/` directory and `AGENTS.md` file.
- **CURSOR**: Pre-configured via the `.cursor/` directory settings.
- **CLAUDE CODE**: Fully supported via the `.claude` folder and `CLAUDE.md` file for the Claude terminal CLI.
- **CODEX**: Compatible through the AI skill definitions located in the `.agents/skills/` directory.

## What is Clean Architecture?

Clean Architecture is a software design philosophy that separates concerns into distinct layers. Relative to people and development teams, it means:

- **Clarity of Intent**: You can understand what the application does just by looking at its structure, without getting bogged down by framework details.
- **Isolation**: Business rules are kept independent of the UI, database, or external APIs.
- **Maintainability**: Changes in one area (like swapping a UI library or upgrading a database) do not ripple through the entire codebase.
- **Testability**: Core logic (unit tests) can be tested without needing the UI, database, or web server to be running. (Note: Backend integration tests start their own throwaway Postgres container, so Docker must be running; web E2E tests require the backend to be running).

## Backend Architecture

<p>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
<img src="https://img.shields.io/badge/SQLAlchemy-008080?style=for-the-badge&logo=sqlalchemy&logoColor=white" />
<img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" />
<img src="https://img.shields.io/badge/Alembic-336791?style=for-the-badge&logo=alembic&logoColor=white" />
<img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
<img src="https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=uvicorn&logoColor=white" />
<img src="https://img.shields.io/badge/Structlog-430098?style=for-the-badge&logo=structlog&logoColor=white" />
<img src="https://img.shields.io/badge/SlowAPI-FF7E00?style=for-the-badge&logo=slowapi&logoColor=white" />
<img src="https://img.shields.io/badge/Ruff-262626?style=for-the-badge&logo=ruff&logoColor=white" />
<img src="https://img.shields.io/badge/MyPy-164081?style=for-the-badge&logoColor=white" />
<img src="https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white" />
</p>

The backend (`server/`) is built with **FastAPI (Async)** and **Python** as a **modular monolith**: code is grouped by business domain, with HTTP routes, application use cases, domain rules, ports, and infrastructure adapters separated inside each module.

- **Modules (`app/modules/<name>/`)**: One folder per domain (`auth`, `users`, `todos`, `attachments`) with `domain/`, `application/ports/`, `application/use_cases/`, `infrastructure/persistence/`, HTTP routes/schemas, and its own DI `container.py`. Generate a layered module with `cd server && uv run python scripts/new_module.py <name>`.
- **Shared (`app/shared/`)**: Reusable building blocks: base repository/service/model, pagination schemas, file storage, integrations.
- **Core (`app/core/`)**: Config, database and unit of work, domain errors and RFC 9457 error handlers, security, logging, middleware.
- **Composition root (`app/container.py`, `app/api.py`, `app/models.py`)**: Wires modules together, mounts routers per API version, registers models for Alembic.
- **Architecture decisions (`docs/adr/`)**: Why the key choices were made.
- **Migrations (`migrations/`)**: Alembic database migration scripts.
- **Tests (`tests/`)**: Pytest suite including unit tests (`tests/unit/`), integration tests (`tests/integrations/`), and mock repository implementations (`tests/mocks/`).
- **Scripts (`scripts/`)**: Application automation and helper scripts.

## Frontend Architecture

<p>
<img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" />
<img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" />
<img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
<img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />
<img src="https://img.shields.io/badge/TanStack-CA4245?style=for-the-badge&logo=reactrouter&logoColor=white" />
<img src="https://img.shields.io/badge/Zod-3E67B1?style=for-the-badge&logo=zod&logoColor=white" />
<img src="https://img.shields.io/badge/Vitest-6E9F18?style=for-the-badge&logo=vitest&logoColor=white" />
<img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" />
<img src="https://img.shields.io/badge/Axios-5A29E4?style=for-the-badge&logo=axios&logoColor=white" />
<img src="https://img.shields.io/badge/Prettier-F7B93E?style=for-the-badge&logo=prettier&logoColor=white" />
<img src="https://img.shields.io/badge/ESLint-4B32C3?style=for-the-badge&logo=eslint&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
<img src="https://img.shields.io/badge/NGINX-009639?style=for-the-badge&logo=nginx&logoColor=white" />
</p>

The frontend (`web/`) is built with **React 19 + TypeScript** and **Vite**. It is designed around modular features and clear separation of state:

- **Features (`src/features/`)**: Modular, page-specific components.
- **Components (`src/components/`)**: Reusable UI components and common elements.
- **Hooks (`src/hooks/`)**: React Query hooks for fetching (`queries/`), modifying (`mutations/`) data, and shared logic (`shared/`).
- **Routes (`src/routes/`)**: File-based routing using TanStack Router.
- **Models (`src/models/`)**: Client-side Zod validation schemas that mirror the backend.
- **Store & Lib (`src/store/`, `src/lib/`)**: Client-side global state and client configuration instances (Axios, QueryClient).
- **Utils & Constants (`src/utils/`, `src/constants/`)**: Shared utility functions and application configurations.
- **Assets (`src/assets/`, `public/`)**: Static files, images, icons, and global styles.
- **Tests (`tests/`)**: Playwright E2E tests (`tests/e2e/`), Vitest unit tests (`tests/unit/`), and mock handlers (`tests/mocks/`).

## Other directories and files

Here is a breakdown of the key folders and files in this repository:

- **`.agents`**: Contains all AI agent skills.
- **`.claude`**: Settings used by Claude.
- **`.cursor`**: Configuration settings specific to the Cursor IDE.
- **`.github`**: CI workflow and Dependabot configuration.
- **`.pre-commit-config.yaml`**: Git hooks for formatting, linting and secret scanning.
- **`.vscode`**: Contains pre-configured tasks and launch settings designed to help you run and debug the code quickly, plus extension recommendations.
- **`docs`**: Contains all the technical documentation for the project.
- **`server`**: Contains the backend code written in FastAPI.
- **`web`**: Contains the React + TypeScript frontend code.
- **`.gitignore`**: Rules to ignore specific files and folders from Git tracking.
- **`AGENTS.md`**: Instructions for Antigravity to read when a session starts.
- **`CLAUDE.md`**: Guidelines and commands for Claude Code and the Claude terminal CLI.
- **`docker-compose.yml`**: Production-like single-host stack (db, redis, migrate, server, worker, web, optional observability profile).
- **`deploy/`**: Helm chart (`helm/app`), Terraform for AWS (`terraform/aws`), observability config (`observability/`), database roles (`db/`) and an Argo CD example (`argocd/`).
- **`docs/`**: API flow, data model, ADRs (`docs/adr`), operations (SLOs, runbooks, deployment, disaster recovery), database guides, governance (data classification, retention, access reviews), security (threat-model template, testing) and the [onboarding guide](docs/onboarding.md).
- **`CONTRIBUTING.md` / `SECURITY.md` / `.github/CODEOWNERS`**: Contribution workflow, vulnerability reporting, code ownership.
- **`LICENSE`**: The open-source license for this repository.
- **`README.md`**: This documentation file.

## Getting Started

For a deeper architectural tour, the 14-area readiness matrix, and a worked example of adding a
domain entity, see the [Development Team Guide](docs/production-template-guide1.html).

Before running or debugging, make sure to:

1. **Open the Project**: Open the root folder in **VS Code** (or your compatible IDE).
2. **Install Extensions**: Accept the prompt to install recommended extensions defined in `.vscode/extensions.json` (such as the Python extension and Code Runner).

You have multiple ways to run the code:

- **Quick Start (Docker Compose)**: Copy `.env.example` to `.env`, fill in the secrets, then run `docker compose up --build`. This starts Postgres, Redis, a one-off migration job, the API (http://localhost:8000), the worker and the web app (http://localhost:3000) with production settings. Add `--profile observability` for Prometheus and Grafana. For real deployments use the Helm chart and Terraform in `deploy/` (see `docs/operations/deployment.md`).
- **Run Both Servers**: You can launch the **FastAPI Backend** and the **React Frontend** simultaneously using the configured "Full Stack" task. This is the fastest way to start working on the entire project. In VS Code, you can trigger this via `Ctrl+Shift+B` (if bound) or through the Run Task menu.
- **Run Individually**: If you are only working on the backend or frontend, you can choose to run just the `Server` or just the `Web` task independently. This helps save system resources.
- **Using Code Runner (Play Button)**: If you have the Code Runner extension installed, you can simply click the Play button in the top right. The project is configured to automatically start the backend server if you run a `.py` file inside the `server/` folder, and start the frontend development server if you run a `.ts` or `.tsx` file in the `web/` folder.
- **Run Tasks (Smart Context)**: Press `Ctrl+Shift+P`, type `Run Task`, and select `🚀 Run: Smart Context`. It automatically detects if you're in frontend or backend code and starts the appropriate server.

## Quality Gates

- **Pre-commit hooks**: Run `uvx pre-commit install --hook-type pre-commit --hook-type pre-push` once. Every commit then runs ruff, prettier, eslint and a gitleaks secret scan; mypy runs on push.
- **Backend tests**: `uv run task test` starts a throwaway Postgres container via [testcontainers](https://testcontainers.com/) (Docker must be running) and rolls back every integration test. Tests refuse `TEST_DB_HOST` overrides because their suite setup recreates the database schema.
- **Coverage gate**: `uv run task cov` fails below 90% backend coverage.
- **CI** (`.github/workflows/ci.yml`): lint, type checks, tests, dependency audit (pip-audit, pnpm audit), SAST (Bandit), secret scan (gitleaks), Docker image build and Trivy scan on every pull request. Dependabot (`.github/dependabot.yml`) opens weekly update PRs.

## Debugging

This project includes fully configured launch settings for attaching an interactive debugger.

- **Launch via F5**: Press `F5` (or go to the Run & Debug tab) to see the launch configurations.
- **Choose Target**: You can choose from `🐍 Debug: Server`, `🌐 Debug: Web`, or `🔥 Debug: Full Stack` to start the respective services with the debugger attached.

## Bonus - What you can learn

If you are here, then you are probably genuinely interested in learning something new. What is here for you? In this section, I am mentioning some of the items which might interest you:

- **Backend Testing**: Learn how to write robust integration and unit tests using **Pytest**.
- **Frontend Testing**: Learn how to write comprehensive E2E and unit tests using **Vitest** and **Playwright**.
- **Advanced Logging**: Implement **Structlog** for structured logging and learn how to attach Request IDs to track request flows.
- **Performance Tracking**: Measure and log API response times using middleware, and track the execution time of database operations.
- **Dependency Injection**: Manage complex application state in Python using the `dependency-injector` package.
- **Pydantic Data Mapping**: Configure Pydantic to seamlessly accept JavaScript (camelCase) object naming conventions and return them in API responses while internally using Python's snake_case.
- **Production SQLAlchemy**: Configure SQLAlchemy connection pooling and engine settings specifically tailored for production environments.
- **SQLAlchemy Eager Loading**: Learn how to optimize database queries by conditionally loading only the required relationships using dynamic `eagers`.
- **Alembic Naming Conventions**: Set up proper metadata naming conventions for constraints and indexes to ensure smooth database migrations and downgrades.
- **Rate Limiting & DI**: Implement rate limiting and understand how it integrates cleanly with dependency injection.
- **Background Tasks & Integrations**: Inject third-party integrations and safely offload heavy workloads to FastAPI background tasks.
- **Health Checks & Readiness**: Validate backend health and ensure successful database connections before executing automatic table migrations.
- **Clean State Management**: Use **TanStack Store** for modular, decoupled frontend state management.
- **Data Fetching & Mutations**: Effectively manage API calls using robust queries and mutations with **TanStack Query**.
- **Type-Safe Forms**: Combine **Zod** schemas with **TanStack Form** for seamless, end-to-end type-safe frontend validation.
- **Optimized Builds**: Leverage advanced **Vite** configurations to drastically improve build performance.
- **Multi-Stage Docker Builds**: Explore how to write optimized, multi-stage Dockerfiles for creating highly lightweight production images.
- **Production Deployment**: Learn how to properly serve the compiled frontend using **NGINX**, which is fully configured to act as a secure reverse proxy for the backend API.

## Have Improvements or Questions?

This repository is completely open for contributions!

- **Have any improvements?** Please raise a PR!
- **Have any questions?** Raise a PR providing the link of the file or line you don't understand, and I will help you with that!

## Note

You might have a lot of questions here: _"Why use this tool and not that one?"_ (e.g., maybe you'd prefer to use SQLModel instead of SQLAlchemy). It completely depends on your specific use case! This repository was created so that I could spin up Proof of Concepts (POCs) extremely quickly without having to set up a full-stack project from scratch again and again. It is not meant to be a "perfect" one-size-fits-all solution, and you will likely want to tweak and configure things to perfectly suit your own needs.

---

<p align="center" style="text">If you liked something about this repository, do give it a 🌟. It will motivate me come up with more such project. You can reach out to me on my social media given below.</p>
<p align="center">
 <a href="https://twitter.com/aps08__"><img src="https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white"></a>
 <a href="https://medium.com/@aps08"><img src="https://img.shields.io/badge/Medium-12100E?style=for-the-badge&logo=medium&logoColor=white"></a>
 <a href="https://www.linkedin.com/in/aps08"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>
 <a href="https://github.com/aps08"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>
 <a href="https://www.youtube.com/channel/UC8biJQnoqm1s2FZ8LK90baA"><img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white"></a>
 <a href="mailto:anoopprsingh@gmail.com"><img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white"></a>
 <a href="https://t.me/aps080"><img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white"></a>
</p>
