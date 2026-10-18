# Writing safe migrations

During a rolling deploy the **old and new app versions run at the same time** against the **same schema**. Every migration must therefore work with both versions. The rule: *the schema is always compatible with the currently deployed code and the code being deployed.*

## Workflow

1. Change the models, then generate: `uv run alembic revision --autogenerate -m "short description"`.
2. **Review the generated file** (autogenerate misses renames, data moves and server defaults; it also cannot judge locking).
3. Run locally: `uv run alembic upgrade head`, `uv run alembic downgrade -1`, `uv run alembic upgrade head`.
4. Update `docs/DATABASE_DESIGN.md`.
5. CI repeats the round-trip on a fresh database and runs `alembic check`.
6. In deployments migrations run as a **separate step before** the new app version rolls out (Helm pre-upgrade hook / pipeline job), with the migration role.

## Expand → migrate → contract

| Change | Release N (expand) | Release N+1 (migrate) | Release N+2 (contract) |
| :--- | :--- | :--- | :--- |
| Add a required column | Add as **nullable** (or with a constant default), code writes it | Backfill in batches; then `SET NOT NULL` | – |
| Rename a column | Add new column; code writes both, reads new with fallback | Backfill; code reads/writes only new | Drop old column |
| Drop a column | Code stops reading/writing it | – | Drop column |
| Change a type | Add new column with new type, dual-write | Backfill, switch reads | Drop old column |
| Add a foreign key / check | Add `NOT VALID` | `VALIDATE CONSTRAINT` (no long lock) | – |

## Locking pitfalls (PostgreSQL)

| Operation | Safe version |
| :--- | :--- |
| `CREATE INDEX` (blocks writes) | `CREATE INDEX CONCURRENTLY` in its own migration with `with op.get_context().autocommit_block():` |
| `ADD COLUMN ... DEFAULT <volatile>` (table rewrite) | Constant defaults only (instant on PG 11+); backfill volatile values in batches |
| `ALTER COLUMN TYPE` (rewrite + lock) | New column + backfill (see above) |
| `SET NOT NULL` on a big table (full scan under lock) | Add `CHECK (col IS NOT NULL) NOT VALID`, validate, then `SET NOT NULL` |
| Long data backfills inside the migration | Batched backfill job (worker), migration only changes schema |

Set a lock timeout at the top of risky migrations so a blocked migration fails fast instead of queueing all traffic behind it:

```python
op.execute("SET lock_timeout = '5s'")
```

## Downgrades

Downgrades must work for schema changes (CI enforces it). For destructive contract steps, the downgrade restores the structure, not the deleted data; restoring data uses backups / PITR (see `docs/operations/disaster-recovery.md`).
