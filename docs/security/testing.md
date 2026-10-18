# Security and resilience testing

| Test | When | How |
| :--- | :--- | :--- |
| Security unit/integration tests | Every PR | pytest: auth flows, CSRF, IDOR, rate limits, lockout, token reuse, upload limits |
| SAST, dependency audit, secret scan, image scan, licences | Every PR | `ci.yml` |
| DAST (OWASP ZAP baseline) | Weekly + before major releases | `.github/workflows/security-scheduled.yml` against staging; triage new alerts like bugs |
| Load & stress tests (k6) | Weekly + before major releases | `.github/workflows/security-scheduled.yml` → `tests/load/smoke.js`; thresholds = performance budget (p95 < 300 ms, < 1% errors) |
| Mutation testing | Weekly on critical code (security, auth service) | `mutmut` job in the scheduled workflow; surviving mutants on security code are treated as missing tests |
| Penetration test | Annually and after major architecture changes | Third party, scoped by the threat models; findings tracked to closure |
| Restore drill | Monthly | `docs/operations/disaster-recovery.md` |

Never run DAST or load tests against production without an agreed window and rate limits; use staging with production-like data volume (synthetic, not copied personal data).
