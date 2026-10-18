# Security Policy

## Reporting a vulnerability

Please **do not open a public issue**. Report vulnerabilities privately through GitHub's "Report a vulnerability" (Security → Advisories) or by email to `security@example.com`. Include the affected component, steps to reproduce and the impact you observed.

We acknowledge reports within 2 working days, give a first assessment within 5, and coordinate disclosure once a fix is released. Please give us a reasonable time to fix before publishing.

## Supported versions

Only the latest release on `main` receives security fixes.

## How security is handled in this project

| Area | Practice | Where |
| :--- | :--- | :--- |
| Dependencies | Lockfiles, weekly Dependabot updates, pip-audit / pnpm audit in CI | `.github/dependabot.yml`, `.github/workflows/ci.yml` |
| Code | SAST (Bandit), secret scanning (gitleaks) in CI and pre-commit | `.pre-commit-config.yaml` |
| Images | Trivy scans, SBOM + provenance attestations, keyless cosign signatures verified before production | `.github/workflows/release.yml` |
| Licences | Licence allow-list check in CI | `.github/workflows/ci.yml` |
| Design | Threat model per significant feature; ADRs for security decisions | `docs/security/threat-model-template.md`, `docs/adr/` |
| Testing | Security behaviour covered by tests (auth, CSRF, IDOR, rate limits); annual third-party penetration test and DAST (OWASP ZAP baseline) against staging | `docs/security/testing.md` |
| Access | Least-privilege IAM and database roles, quarterly access reviews | `docs/governance/access-control.md` |
