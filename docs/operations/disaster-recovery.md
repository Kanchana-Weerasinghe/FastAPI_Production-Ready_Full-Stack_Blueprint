# Backups and Disaster Recovery

## Objectives

| Data | RPO (max data loss) | RTO (max downtime) | How |
| :--- | :--- | :--- | :--- |
| PostgreSQL | 5 minutes | 1 hour | Managed Postgres (RDS/Cloud SQL/Azure) with continuous WAL archiving → point-in-time recovery (PITR), daily snapshots, 35-day retention |
| Object storage (uploaded files, when a module uses `FileStorage`) | 0 (versioned) | 1 hour | S3 versioning + replication to a second region, lifecycle rules for old versions |
| Redis | Not backed up | Minutes | Holds only rate-limit counters and the job queue; outbox events live in Postgres, so nothing durable is lost |
| Secrets | 0 | 1 hour | Secrets manager with replication; break-glass access documented separately |

## Backups

- Enable automated backups + PITR on the managed database; encrypt with a KMS key; copy snapshots to another region/account (protects against account compromise and regional outage).
- Backups are only useful if restores work: a **restore drill runs monthly** (below). An untested backup counts as no backup.
- Never rely on `pg_dump` from a laptop as the backup strategy; it is fine for ad-hoc copies.

## Restore drill (monthly, ~1 hour)

1. Restore the latest snapshot / a PITR timestamp from 1 hour ago into a **new** instance in staging.
2. Point a staging deployment at it (`DB_HOST`), run `alembic current` (expect `head`), and run the smoke tests.
3. Verify row counts of key tables against production metrics and spot-check recent records.
4. Record the measured restore time (compare with RTO) and data timestamp (compare with RPO) in the drill log; file issues for gaps.
5. Destroy the restored instance.

## Disaster scenarios

| Scenario | Response |
| :--- | :--- |
| Bad migration / accidental delete | Stop writes (scale to 0 or maintenance mode), PITR to just before the event into a new instance, verify, switch `DB_HOST`, replay safe writes from logs/outbox if needed. |
| Database instance failure | Managed failover to the standby (multi-AZ); app reconnects (`pool_pre_ping`). |
| Region outage | Restore latest cross-region snapshot/PITR in the DR region, deploy the same image via the IaC pipeline, update DNS. |
| Leaked credentials | Rotate in the secrets manager (`SECRET_KEY` rotation signs everyone out; DB password via dual-user rotation), redeploy, review audit logs. |
| Ransomware / account compromise | Restore from the isolated backup account; rotate all credentials. |

## Ownership

The service owner reviews this document quarterly and after every incident that touched data.
