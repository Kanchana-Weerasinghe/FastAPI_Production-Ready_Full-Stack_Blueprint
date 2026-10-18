# Service Level Objectives

SLOs define how reliable the service must be, so trade-offs between shipping features and reliability work are explicit. Adjust the targets to your product; keep the structure.

## SLIs and SLOs

| SLI | Definition (measured at the load balancer / API metrics) | SLO (28-day rolling) |
| :--- | :--- | :--- |
| Availability | Share of requests that do not return 5xx (429 excluded) | 99.9% |
| Latency | Share of requests served faster than 300 ms (p95 target) / 1 s (p99 target) | 95% < 300 ms, 99% < 1 s |
| Background delivery | Share of outbox events delivered within 5 minutes of commit | 99% |
| Dead letters | Outbox events reaching `dead` | 0 unresolved for > 24 h |

Health endpoints (`/health/*`), and requests rejected by rate limiting are excluded from the availability SLI.

## Error budget

- 99.9% availability over 28 days ≈ **40 minutes** of failed requests (or the equivalent share of requests).
- **Budget remaining > 0**: normal feature work.
- **Budget burned faster than 2× the sustainable rate for 1 h, or 50% consumed**: page on-call (see alerts below).
- **Budget exhausted**: freeze risky releases; prioritise reliability fixes until the budget recovers. Exceptions require sign-off by the service owner.

## Alerts (multi-window burn rate)

| Alert | Condition | Severity | Runbook |
| :--- | :--- | :--- | :--- |
| `HighErrorBudgetBurn` | 5xx ratio > 14.4× budget rate over 1 h **and** 5 min | Page | [runbooks/high-error-rate.md](runbooks/high-error-rate.md) |
| `SlowErrorBudgetBurn` | 5xx ratio > 6× budget rate over 6 h **and** 30 min | Ticket | [runbooks/high-error-rate.md](runbooks/high-error-rate.md) |
| `HighLatency` | p99 > 1 s for 15 min | Page | [runbooks/high-latency.md](runbooks/high-latency.md) |
| `OutboxBacklog` | Oldest pending outbox event older than 10 min | Page | [runbooks/outbox-backlog.md](runbooks/outbox-backlog.md) |
| `OutboxDeadLetters` | Any event in `dead` status | Ticket | [runbooks/outbox-backlog.md](runbooks/outbox-backlog.md) |
| `ReadinessFailing` | Readiness probe failing on > 50% of pods for 5 min | Page | [runbooks/dependency-down.md](runbooks/dependency-down.md) |

Metric names and dashboards are defined with the observability stack (Prometheus/OpenTelemetry); see `docs/operations/observability.md`.
