# 0015. Governance: privacy rights, retention, feature flags and supply-chain policy

- Status: Accepted
- Date: 2026-10-16

## Context

A production service holding personal data must honour data-subject rights, limit storage, control who can access what, decouple releases from deploys, and keep its dependency licences and supply chain in check.

## Decision

- **Privacy rights**: a `privacy` module exports everything stored about a user (`GET /v2/user/me/export`, audited); account deletion is the erasure path. The personal-data inventory in `docs/governance/data-classification.md` is updated with every new field (PR checklist) and drives the export.
- **Retention**: defined per data type in `docs/governance/data-retention.md` and enforced by the worker's daily purge job (`AUDIT_LOG_RETENTION_DAYS`, token/outbox/idempotency expiry).
- **Encryption**: TLS in transit everywhere; encrypted storage at rest; field-level encryption (`encrypt_field`) for secrets and special-category data.
- **Access**: least privilege for people and workloads, OIDC/IRSA instead of static keys, quarterly access reviews (`docs/governance/access-control.md`).
- **Feature flags**: a small database-backed `flags` module (enable/disable, role targeting, deterministic percentage rollout, 30-second per-process cache, audited changes, `require_flag(...)` for routes, `/v2/feature-flags/me` for the web app). Chosen over a SaaS (LaunchDarkly/Unleash) to keep the template self-contained; swap the service implementation if experiments or targeting rules outgrow it.
- **Supply chain & licences**: lockfiles, Dependabot, pip-audit/pnpm audit, Bandit, gitleaks, Trivy, SBOM + provenance, signed images, and a CI licence check denying strong-copyleft licences.
- **Process**: CODEOWNERS, PR template, Conventional Commits, threat model per significant feature, scheduled DAST/load/mutation testing, annual penetration test.

## Consequences

- Flags are temporary: each flag needs an owner and a removal date in its description; stale flags are cleaned up regularly.
- Legal review is still required for the privacy notice, lawful bases and retention periods; the documents here are engineering defaults, not legal advice.
