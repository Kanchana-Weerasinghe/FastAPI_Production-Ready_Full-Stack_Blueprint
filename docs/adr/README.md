# Architecture Decision Records

An ADR captures one significant decision: the context, the choice, and its consequences. ADRs are immutable once accepted; to change a decision, add a new ADR that supersedes the old one and update the old one's status.

## Index

| ADR | Title | Status |
| :--- | :--- | :--- |
| [0001](0001-modular-monolith.md) | Modular monolith with per-module DI containers | Accepted |
| [0002](0002-rfc9457-error-format.md) | Domain errors rendered as RFC 9457 Problem Details | Accepted |
| [0003](0003-api-versioning.md) | URL major versioning and deprecation policy | Accepted |
| [0004](0004-unit-of-work.md) | One transaction per request with after-commit side effects | Accepted |
| [0005](0005-private-file-storage.md) | Private file storage behind authenticated downloads | Accepted |
| [0006](0006-rate-limiting-and-client-ip.md) | Shared rate-limit storage and trusted-proxy client IPs | Accepted |
| [0007](0007-fail-closed-configuration.md) | Fail-closed configuration outside development | Accepted |
| [0008](0008-session-tokens.md) | Session tokens, revocation, CSRF and MFA | Accepted |
| [0009](0009-authorization-rbac.md) | Authorization: RBAC in code plus central ownership checks | Accepted |
| [0010](0010-background-jobs-and-outbox.md) | Background jobs (ARQ) and the transactional outbox | Accepted |
| [0011](0011-observability.md) | Observability: logs, metrics, traces, errors and audit | Accepted |
| [0012](0012-data-layer.md) | Data layer: migrations, concurrency, pooling and tenancy | Accepted |
| [0013](0013-deployment.md) | Containers on Kubernetes, infrastructure as code, build once and promote | Accepted |
| [0014](0014-frontend.md) | Frontend: secure sessions, resilience, monitoring, budgets and accessibility | Accepted |
| [0015](0015-governance-and-feature-flags.md) | Governance: privacy rights, retention, feature flags and supply-chain policy | Accepted |
| [0016](0016-independent-domain-services.md) | Independent domain services with a shared platform kit | Accepted |

## Template

Copy this into `NNNN-short-title.md` (next free number):

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context

What problem are we solving? Which forces and constraints apply?

## Decision

What we will do, stated in full sentences.

## Consequences

What becomes easier or harder; follow-up work; risks accepted.
```
