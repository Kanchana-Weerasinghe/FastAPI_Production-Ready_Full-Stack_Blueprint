# Data classification and personal data inventory

## Classes

| Class | Definition | Handling |
| :--- | :--- | :--- |
| **Secret** | Credentials and keys: password hashes, refresh/one-time token hashes, MFA seeds, API keys | Never logged or exported; hashed or encrypted at rest; access only by the service itself |
| **Confidential (personal)** | Data about an identifiable person: email, IP address, user agent, user content (todos, files) | Encrypted in transit and at rest; only the owner and authorised staff (audited); exported on request; deleted per retention |
| **Internal** | Operational data without personal content: outbox events (after delivery), metrics | Access limited to the team |
| **Public** | Marketing pages, API documentation | No restrictions |

## Encryption

- **In transit**: TLS everywhere: client → load balancer/ingress (HSTS), service → Postgres (`rds.force_ssl`), service → Redis (`rediss://`), service → S3 (HTTPS).
- **At rest**: encrypted storage for Postgres (KMS), Redis, S3 (SSE-KMS) and backups/snapshots.
- **Field level**: secrets that must be readable by the service (MFA seeds) are encrypted with `FIELD_ENCRYPTION_KEY` (`encrypt_field`); passwords use bcrypt; tokens are stored as SHA-256 hashes. Use `encrypt_field` for any new field holding special-category data (health, financial identifiers) and keep it out of filters/indexes.

## Personal data inventory

Update this table with every new field that holds personal data (PR checklist).

| Store | Field(s) | Class | Purpose | Lawful basis | Retention | In export |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `users` | `email`, `username` | Confidential | Account, sign-in, notifications | Contract | Until account deletion | Yes |
| `users` | `password`, `mfa_secret_encrypted` | Secret | Authentication | Contract | Until account deletion / change | No (secret) |
| `todos` | `title`, `description` | Confidential | Core feature | Contract | Until deleted by user or account deletion | Yes |
| `refresh_tokens` | `ip_address`, `user_agent` | Confidential | Session security | Legitimate interest | 7 days after expiry/revocation | No (purged quickly) |
| `audit_logs` | `actor_id`, `ip_address`, `user_agent` | Confidential | Security monitoring, fraud prevention, compliance | Legitimate interest / legal obligation | `AUDIT_LOG_RETENTION_DAYS` (400) | Yes (security events) |
| Logs (stdout → log platform) | `client_ip`, `request_id` (emails masked) | Confidential | Operations, debugging | Legitimate interest | Log platform retention (30 days recommended) | No |
| Sentry | release, URL, stack traces (PII scrubbed) | Internal | Error tracking | Legitimate interest | Sentry retention (90 days) | No |

## Data subject rights

| Right | Implementation |
| :--- | :--- |
| Access / portability (GDPR art. 15, 20; CCPA right to know) | Not implemented in the template; add an audited export endpoint before handling personal data under GDPR/CCPA |
| Erasure (art. 17; CCPA delete) | `DELETE /v2/user/me`: deletes the account, content and stored files (audit entry kept without content, per legitimate interest) |
| Rectification (art. 16) | Users edit their content; email changes via support until a self-service flow is added |
| Restriction / objection | Handled by support; add a `processing_restricted` flag on the account if volumes require it |
| Consent | Not needed for the current processing (contract / legitimate interest). If you add marketing email or non-essential cookies/analytics, record consent (purpose, timestamp, version) and honour withdrawal |

## HIPAA / special categories

The template stores no health data. Before storing PHI: sign a BAA with every processor, use field-level encryption for PHI, extend audit logging to every read of PHI, and review the retention and backup policies.
