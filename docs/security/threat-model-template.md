# Threat model: <feature name>

Create one per significant feature (new data, new external integration, new permission, new public endpoint) before implementation; review it in the design PR. Keep it short and specific.

## 1. Scope

- What is being built, who uses it, which data it touches (classes from `docs/governance/data-classification.md`).
- Diagram: actors, components, data stores, trust boundaries (browser ↔ API, API ↔ DB, API ↔ third parties).

## 2. Threats (STRIDE)

| # | Category | Threat | Affected component | Likelihood | Impact | Mitigation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Spoofing | e.g. stolen session cookie reused | Auth | Medium | High | Short-lived access token, refresh rotation + reuse detection | Done |
| 2 | Tampering | e.g. user edits another user's resource (IDOR) | API | Medium | High | `check_ownership`, tests for cross-user access | |
| 3 | Repudiation | e.g. admin denies changing a setting | Admin API | Low | Medium | Audit log entry with actor, IP, request id | |
| 4 | Information disclosure | e.g. PII in logs or error messages | Logging | Medium | High | Redaction processor, RFC 9457 generic 500s | |
| 5 | Denial of service | e.g. huge uploads, expensive queries | API/DB | Medium | Medium | Size limits, page-size caps, rate limits, statement timeout | |
| 6 | Elevation of privilege | e.g. user reaches admin endpoint | API | Low | High | `require_permission`, tests | |

## 3. Abuse cases & tests

List the malicious scenarios as test cases (integration tests or ZAP rules) that must exist before release.

## 4. Residual risks

Risks accepted, with owner and review date.
