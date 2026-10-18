# 0011. Observability: logs, metrics, traces, errors and audit

- Status: Accepted
- Date: 2026-10-16

## Context

The service only emitted JSON logs with a per-request id. There were no metrics, traces, error tracking, alerts or audit trail, so incidents could not be detected, diagnosed or reviewed.

## Decision

- **Vendor-neutral standards**: Prometheus exposition format for metrics and OpenTelemetry (OTLP) for traces, so any backend (Grafana stack, Datadog, Honeycomb, cloud APMs) can be used without code changes.
- **Logs**: structured JSON with correlation fields (`request_id`, `trace_id`, `service`, `version`, `env`); a redaction processor drops secret-looking keys and masks emails.
- **Metrics**: RED per route template plus saturation/backlog gauges; multiprocess-safe for gunicorn. `/metrics` is never public (token or network policy).
- **Traces**: opt-in, head-sampled (`ParentBased(TraceIdRatioBased)`), health and metrics endpoints excluded.
- **Errors**: Sentry, opt-in via DSN, tagged with the release; request headers/cookies/bodies scrubbed.
- **Audit**: a dedicated `audit` module (append-only table) records security-relevant and administrative actions in the same transaction as the action; failures (e.g. bad passwords) are persisted although the request fails.
- **Alerting** follows the SLOs (multi-window burn rates); every alert has a runbook.

## Consequences

- Teams must keep metric labels bounded and add a runbook with every alert.
- The audit table grows indefinitely; export to cold storage/SIEM and apply a retention policy agreed with compliance (see the data-retention policy).
