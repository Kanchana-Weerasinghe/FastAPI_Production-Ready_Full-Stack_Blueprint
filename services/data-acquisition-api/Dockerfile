# syntax=docker/dockerfile:1.7
# Production image for data-acquisition-api.
# Build from the repository root so the shared platform-kit package is in the context:
#   docker build -f services/data-acquisition-api/Dockerfile -t data-acquisition-api .

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    # Create the venv at its final path: console-script shebangs embed the venv location.
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

# Same relative layout as the repository, so the `../../packages/platform-kit` path source resolves.
WORKDIR /src
COPY packages/platform-kit ./packages/platform-kit
COPY services/data-acquisition-api/pyproject.toml services/data-acquisition-api/uv.lock ./services/data-acquisition-api/
WORKDIR /src/services/data-acquisition-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable


FROM ${PYTHON_IMAGE} AS runtime

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="data-acquisition-api" \
      org.opencontainers.image.version="${APP_VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION}

RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --chown=root:root services/data-acquisition-api/alembic.ini ./
COPY --chown=root:root services/data-acquisition-api/app ./app
COPY --chown=root:root services/data-acquisition-api/migrations ./migrations

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--graceful-timeout", "30"]
