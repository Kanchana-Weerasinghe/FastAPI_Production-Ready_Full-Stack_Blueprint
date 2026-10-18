# Runbook: High error rate (HighErrorBudgetBurn / SlowErrorBudgetBurn)

**Impact:** users see 5xx errors; the availability SLO budget is burning.

## Triage (first 10 minutes)

1. Open the **API Overview** dashboard: which routes produce 5xx? Did it start with a deploy (check release annotations / `APP_VERSION` in logs)?
2. Sentry: filter by `release` and `environment`; the top new issue is usually the cause.
3. Logs: `level=error` and `event=unhandled_exception`, grouped by `path`. Every error response carries `request_id`; use it to pull the full request log and trace (`trace_id`).
4. Check dependencies: `/health/ready` on the pods, database and Redis status, `circuit_breaker_opened` log events for third parties.

## Mitigate

- **Bad release** → roll back to the previous image (`helm rollback api <revision>` or redeploy the previous tag). Do this first, debug later.
- **Database overloaded / pool exhausted** → see [high-latency.md](high-latency.md).
- **Third-party outage** → the circuit breaker fails fast; consider a feature flag to disable the dependent feature.
- **Traffic spike / abuse** → tighten rate limits or block at the WAF; scale out (`kubectl scale` / HPA max).

## Follow-up

Write a post-incident review within 5 working days if the incident consumed more than 20% of the monthly error budget.
