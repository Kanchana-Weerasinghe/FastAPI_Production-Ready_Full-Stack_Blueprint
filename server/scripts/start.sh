#!/bin/bash
# Container entrypoint for the API.
#
# Migrations are a separate deployment step (Helm pre-upgrade Job / Compose `migrate` service), so
# replicas never race to migrate. Set RUN_MIGRATIONS=true only for single-instance setups.

set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:."

if [[ "${RUN_MIGRATIONS:-false}" == "true" ]]; then
  echo "[START] Checking database connection..."
  python scripts/backend_pre_start.py
  echo "[START] Running database migrations..."
  alembic upgrade head
fi

# Aggregate Prometheus metrics across gunicorn workers (fresh directory on every start).
export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}"
rm -rf "$PROMETHEUS_MULTIPROC_DIR" && mkdir -p "$PROMETHEUS_MULTIPROC_DIR"

echo "[START] Starting Gunicorn with ${WEB_CONCURRENCY:-4} worker processes..."
# --graceful-timeout: on SIGTERM finish in-flight requests before exiting (keep it below the
#   orchestrator's termination grace period). --max-requests(+jitter) recycles workers to cap leaks.
exec gunicorn app.main:app \
  --config gunicorn.conf.py \
  --bind 0.0.0.0:8000 \
  --workers "${WEB_CONCURRENCY:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-tmp-dir /tmp \
  --timeout 60 \
  --graceful-timeout 25 \
  --keep-alive 5 \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --log-level warning
