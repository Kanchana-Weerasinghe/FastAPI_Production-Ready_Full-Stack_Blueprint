# 0004. One transaction per request with after-commit side effects

- Status: Accepted
- Date: 2026-10-16

## Context

Exception handlers convert errors into normal responses, so the request-scoped session committed even when a request failed halfway (e.g. a todo was saved although linking an attachment returned 404). Side effects such as deleting files or sending emails ran before the transaction committed, so a rollback left the system inconsistent.

## Decision

- `CoreMiddleware` opens one transaction per request (`Database.session_scope`) and commits it once. Any response with status ≥ 400 rolls it back.
- Services and repositories never commit; repositories only `flush`.
- Services receive a `UnitOfWork` and register side effects with `uow.after_commit(func, *args)`. They run only after a successful commit, as response background tasks for HTTP requests or inline for scripts/workers using `session_scope()`. A failing callback is logged and never undoes the commit.
- A service may call `uow.persist_on_failure()` on paths whose only writes are security bookkeeping that must survive the failing response (failed-login counter, revoking a stolen refresh-token family). After-commit callbacks are still discarded.
- Background jobs (Phase 4 workers) open their own `session_scope()` per job.

## Consequences

- A request is atomic: all of its writes persist or none do.
- After-commit callbacks are best-effort and in-process: a crash between commit and callback loses the side effect. Side effects that must not be lost (payments, outbound events) go through the transactional outbox instead (see the reliability ADRs).
- Long-running work inside a request still holds the transaction open; move it to a background job.
