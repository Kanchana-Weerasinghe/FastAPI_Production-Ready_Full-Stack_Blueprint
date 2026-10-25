# Observability

| Signal | Implementation | Where to look |
| :--- | :--- | :--- |
| Logs | structlog JSON to stdout: `request_id`, `trace_id`/`span_id`, `service`, `version`, `env`, `client_ip`; secrets redacted and emails masked (`app/core/logging.py`) | Your log platform (Loki, CloudWatch, Datadog, ...) |
| Correlation | `X-Request-ID` accepted from the caller (or generated), returned on every response and in every error body, forwarded to outbound HTTP calls | Search logs by `request_id` |
| Metrics | Prometheus at `/metrics`: RED (`http_requests_total`, `http_request_duration_seconds` by route template), saturation (`db_pool_*`), backlog (`outbox_*`); aggregated across gunicorn workers | Grafana dashboard `deploy/observability/grafana/dashboards/api-overview.json` |
| Traces | OpenTelemetry (FastAPI, SQLAlchemy, httpx), OTLP/HTTP export, parent-based ratio sampling (`OTEL_TRACES_SAMPLE_RATIO`) | Tempo / Jaeger / your APM |
| Errors | Sentry with `release=APP_VERSION`, `environment`, headers/cookies/bodies scrubbed | Sentry |
| Audit | `audit_logs` table: sign-ins (success/failure), lockouts, refresh-token reuse, password and MFA changes, account deletion; `GET /v2/audit-logs/` (permission `audit:read`) | Admin API / SQL; ship to a SIEM for retention |
| Alerts | `deploy/observability/alerts.yml`, tied to the SLOs in [slo.md](slo.md), each with a runbook | Alertmanager → paging |

## Configuration

| Variable | Purpose |
| :--- | :--- |
| `APP_VERSION` | Release identifier set by CI (git SHA or semver); tags logs, traces and Sentry events |
| `LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE` | Enable Sentry |
| `OTEL_ENABLED`, `OTEL_SERVICE_NAME`, `OTEL_TRACES_SAMPLE_RATIO`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Enable tracing (point the endpoint at an OpenTelemetry Collector) |
| `METRICS_ENABLED`, `METRICS_TOKEN` | Expose `/metrics`; require a bearer token if it is reachable beyond the cluster network |

## Local stack

`docker compose --profile observability up` starts Prometheus (http://localhost:9090, alert rules loaded) and Grafana (http://localhost:3001, anonymous viewer, dashboard pre-provisioned) next to the app.

## Conventions

- Log **events**, not sentences: `logger.info("project_created", project_id=...)`. Never log secrets, tokens, passwords or raw request bodies; the redaction processor is a safety net, not a licence.
- Label metrics with bounded values only (route templates, status codes), never user IDs or raw paths.
- Every new alert needs a runbook under `docs/operations/runbooks/` and must map to user impact.
