# Runbook: High latency (HighLatency / DatabasePoolSaturated)

**Impact:** slow pages and timeouts; may turn into errors when clients or the load balancer time out.

## Triage

1. Dashboard: is it all routes (systemic) or a few (specific queries)? Compare with request rate.
2. Traces (OpenTelemetry): open slow traces for the worst route and look for long SQL spans or outbound HTTP spans.
3. `db_pool_connections_in_use` near `db_pool_size`: requests are queueing for connections.
4. Database: active queries / locks (`pg_stat_activity`, `pg_locks`), CPU, IOPS, slow query log.
5. Pods: CPU throttling and memory (event-loop blocking shows up as high latency with low DB time).

## Mitigate

- **Missing index / bad query plan** → add the index with `CREATE INDEX CONCURRENTLY` in a migration; ship as a hotfix.
- **Lock contention** (e.g. long migration or batch job) → stop the offending job; cancel the blocking query.
- **Pool exhaustion** → scale out pods only if the database has headroom (`replicas × workers × (pool_size + max_overflow)` must stay below Postgres `max_connections`; use PgBouncer for many replicas).
- **CPU-bound work on the event loop** → move it to a thread pool or the worker.
