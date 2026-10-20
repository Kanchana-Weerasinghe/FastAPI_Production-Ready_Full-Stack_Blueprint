# syntax=docker/dockerfile:1.7
# Production image for the API and the worker (same image, different command).
# - Multi-stage: build tools and uv stay in the builder; the runtime has only the venv and app code.
# - Runs as a fixed non-root UID and works with a read-only root filesystem (writable: /tmp, uploads).
# - Pin base images by digest in your registry mirror (Dependabot/Renovate keep them updated).

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


FROM ${PYTHON_IMAGE} AS runtime

ARG APP_VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="api" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/your-org/your-repo"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION} \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --chown=root:root alembic.ini gunicorn.conf.py ./
COPY --chown=root:root app ./app
COPY --chown=root:root migrations ./migrations
COPY --chown=root:root scripts ./scripts

# Code is owned by root and read-only for the app user; only the upload dir is writable
# (mount a volume there, or use STORAGE_BACKEND=s3 and drop it).
RUN mkdir -p /app/uploads && chown app:app /app/uploads && chmod 0555 scripts/start.sh

USER 10001:10001
EXPOSE 8000

# Container-level healthcheck for Docker/Compose; Kubernetes uses the probes in the Helm chart.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"]

CMD ["scripts/start.sh"]
