# Data retention

Keep personal data only as long as needed for its purpose (GDPR storage limitation). Retention is enforced automatically where possible (`purge_expired_records` worker job, daily at 03:15 UTC).

| Data | Retention | Enforcement |
| :--- | :--- | :--- |
| Account, todos | Until the user deletes them or the account | User actions (`DELETE` endpoints) |
| Inactive accounts | Define per product (e.g. notify after 24 months, delete after 36) | Add a scheduled job when the policy is agreed |
| Refresh tokens | Expiry + 7 days (revoked: revocation + 7 days) | Worker job |
| Email verification / password reset tokens | Expiry/use + 7 days | Worker job |
| Idempotency keys | `IDEMPOTENCY_TTL_HOURS` (24 h) | Worker job |
| Delivered outbox events | 7 days | Worker job |
| Dead-lettered outbox events | Until resolved (replayed or deleted by an operator) | Runbook |
| Audit logs | `AUDIT_LOG_RETENTION_DAYS` (400 days) | Worker job; export to the SIEM/archive first if longer retention is legally required |
| Application logs | 30 days (log platform setting) | Log platform |
| Database backups / PITR | 35 days | Managed database setting (Terraform) |
| Object storage previous versions | 30 days | S3 lifecycle rule (Terraform) |

Deleted data disappears from backups as they age out (35 days); document this in the privacy notice.
