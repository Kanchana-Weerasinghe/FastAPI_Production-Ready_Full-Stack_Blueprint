# 0012. Data layer: migrations, concurrency, pooling and tenancy

- Status: Accepted
- Date: 2026-10-16

## Context

A large application needs zero-downtime schema changes, protection against lost updates, predictable connection usage, a path to read scaling, and a stated position on multi-tenancy, before the first production deploy rather than after.

## Decision

- **Migrations** are Alembic revisions reviewed like code, applied as a separate deployment step (never by app replicas racing at start-up in production), and must be **backward compatible with the previous app version** using expand → migrate → contract (see `docs/database/migrations.md`). CI runs upgrade → downgrade base → upgrade and `alembic check` (models = migrations) on every change.
- **Least privilege**: the app connects as a DML-only role; migrations run as a separate owner role (`MIGRATION_DB_USERNAME`). See `deploy/db/roles.sql`.
- **Integrity in the database**: uniqueness, foreign keys and NOT NULL live in the schema; violations map to 409 `conflict`. Statement timeout (`DB_STATEMENT_TIMEOUT_MS`) protects the database from runaway queries.
- **Optimistic locking** on every table (`version` column, SQLAlchemy `version_id_col`): concurrent ORM updates raise 409 `concurrent_modification`; HTTP clients use `ETag`/`If-Match` (412 `precondition_failed`) via `app/core/conditional.py`.
- **Soft delete** is available per repository (`soft_delete`, all reads exclude `is_deleted`); use it where data must stay recoverable or auditable, with a purge job per retention policy. Hard delete stays the default when the user explicitly deletes their data (privacy).
- **Pagination**: offset pagination with a hard page-size cap for small, user-scoped lists; keyset (cursor) pagination for large/append-heavy tables (audit log).
- **Pooling**: per-process SQLAlchemy pool (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`, `pool_pre_ping`). Budget: `replicas × workers × (pool + overflow) + workers(jobs) < max_connections − headroom`. Beyond that, put **PgBouncer** (transaction mode) in front and set `DB_PGBOUNCER=true`.
- **Performance budgets**: statements over `DB_SLOW_QUERY_MS` are logged (`slow_query`) and p95 latency per route is alerted on. Every new query pattern on a large table ships with its index (`CREATE INDEX CONCURRENTLY` in a separate migration).
- **Read replicas**: not enabled by default. When needed, add a second engine for read-only use cases (reports, exports, listings tolerant to replication lag) behind a `ReadOnlyUnitOfWork`; never read-your-own-writes from a replica.
- **Multi-tenancy**: not built in. If required, prefer **row-level tenancy** (`tenant_id` on every tenant-owned table, enforced by repositories plus PostgreSQL Row-Level Security as a backstop); use schema- or database-per-tenant only for strict isolation/compliance needs.
- **Seeding** is development-only (`scripts/seed_dev.py`, refuses to run elsewhere); production bootstrap is a one-off, audited job (`scripts/create_admin.py`).

## Consequences

- Every update increments `version`; Core `UPDATE` statements must bump it explicitly.
- Breaking schema changes take at least two releases (expand, then contract).
