# 0010. Background jobs (ARQ) and the transactional outbox

- Status: Accepted
- Date: 2026-10-16

## Context

Emails were sent from FastAPI `BackgroundTasks` (later after-commit callbacks) inside the web process: a crash or deploy between commit and send lost the email, provider outages were not retried, and nothing recorded failures. Slow work (reports, exports) had nowhere to run except the request.

## Decision

- **Worker**: [ARQ](https://arq-docs.helpmanual.io/) on Redis (`app/worker.py`, `arq app.worker.WorkerSettings`), chosen over Celery because the codebase is async end to end and ARQ reuses the same async services. Jobs are enqueued with `TaskQueue.enqueue(...)`, retried up to `max_tries` (raise `arq.Retry(defer=...)` for backoff) and time-boxed by `job_timeout`.
- **Transactional outbox** (`app/shared/outbox.py`): side effects and integration events are rows in `outbox_events`, written in the same transaction as the business change. An event exists if and only if the change committed.
- **Relay**: the worker polls due events every 5 seconds (`SELECT ... FOR UPDATE SKIP LOCKED`, so several workers can run), dispatches them to handlers registered in the container, and on failure retries with exponential backoff (`available_at`). After `OUTBOX_MAX_ATTEMPTS` the event becomes `dead`: the **dead-letter queue**. Dead events are alerted on and can be replayed by resetting `status='pending', attempts=0`.
- **Email** goes through the outbox: services use `OutboxEmailSender` (the `EmailSender` port); the `email.send` handler calls the provider transport.
- **Development**: `OUTBOX_DISPATCH_INLINE` (default on in development and tests) delivers each event right after commit in-process, so no worker is needed locally.
- Maintenance runs as worker cron jobs (purging delivered events and expired auth tokens).

## Consequences

- Delivery is **at-least-once**: handlers must be idempotent (e.g. deduplicate on the event id).
- Redis becomes required in deployed environments (worker queue); the readiness probe checks it when `REDIS_URL` is set.
- A batch holds row locks while handlers call external services; keep handlers fast, or move slow work into separate ARQ jobs triggered by the handler.
- `outbox_events` grows with traffic; delivered rows are purged after 7 days, dead rows kept until resolved.
