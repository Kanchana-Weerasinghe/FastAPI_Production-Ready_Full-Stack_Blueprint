# Runbook: Outbox backlog or dead letters (OutboxBacklog / OutboxDeadLetters)

**Impact:** emails and other side effects are delayed (backlog) or not delivered at all (dead letters).

## Triage

1. Is the worker running? `kubectl get pods -l app.kubernetes.io/component=worker`, worker logs (`worker_started`, `outbox_event_failed`).
2. Is Redis reachable from the worker (`REDIS_URL`)? The relay cron depends on it.
3. What is failing? Inspect recent failures:

   ```sql
   SELECT event_type, status, attempts, last_error, created_at
   FROM outbox_events
   WHERE status IN ('pending', 'dead') AND attempts > 0
   ORDER BY created_at DESC LIMIT 50;
   ```

4. Provider outage? Check the provider status page and `circuit_breaker_opened` logs.

## Mitigate

- **Worker down** → restart/scale the worker deployment. Pending events are delivered automatically.
- **Provider outage** → nothing to do; events retry with backoff. If the outage outlasts `OUTBOX_MAX_ATTEMPTS`, replay dead letters afterwards.
- **Bug in a handler** → fix and deploy, then replay.

## Replay dead letters

Handlers are idempotent, so replaying is safe:

```sql
UPDATE outbox_events
SET status = 'pending', attempts = 0, available_at = now(), last_error = NULL
WHERE status = 'dead' AND event_type = 'email.send';
```
