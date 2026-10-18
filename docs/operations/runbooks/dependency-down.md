# Runbook: Dependency down (ReadinessFailing / TargetDown)

**Impact:** pods are removed from load balancing; if all are unready the API is down.

## Triage

1. `kubectl describe pod` / `kubectl logs`: what does `/health/ready` report? The 503 `detail` names the failing dependency (database or Redis) or `shutting_down`.
2. Database: managed instance status, failover events, connection limits, credentials rotation (auth failures in logs).
3. Redis: instance status and memory (eviction or OOM).
4. Network: security groups / network policies changed recently?

## Mitigate

- **Database failover in progress** → wait; `pool_pre_ping` reconnects automatically. If credentials were rotated, update the secret and restart pods.
- **Redis down** → rate limiting and the job queue are affected; the API still serves requests once Redis is back. Restore Redis (no durable data is kept there; the outbox lives in Postgres).
- **Pods crash-looping** → check the last log lines: a fail-fast configuration error (missing/insecure secret) means the deployment's secrets are wrong.

Liveness (`/health/live`) never checks dependencies, so an outage does not trigger restart storms.
