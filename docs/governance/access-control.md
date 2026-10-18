# Access control and reviews

## Principles

- **Least privilege** for people and workloads; no shared accounts; MFA for every human account (cloud console, GitHub, Sentry, log platform).
- **Workload identities** instead of static keys: GitHub Actions → cloud via OIDC (`AWS_DEPLOY_ROLE_ARN`), pods → S3 via IRSA (service account annotation), no long-lived access keys in CI or in the cluster.
- **Database**: the app uses a DML-only role (`app_rw`), migrations a separate owner role (`deploy/db/roles.sql`); humans get read-only, time-boxed access through a bastion/SSM with session logging. No database ports are exposed publicly.
- **Production changes** only through the pipeline (reviewed PR → approved deployment). Break-glass access is time-limited, alerted and reviewed afterwards.
- **Application roles**: `user` and `admin` (`app/modules/auth/permissions.py`). Granting `admin` is done with the audited bootstrap script and recorded in the audit log.

## Quarterly access review

| Scope | Reviewer | Evidence |
| :--- | :--- | :--- |
| GitHub org/teams, CODEOWNERS, branch protection | Engineering manager | Export of members/teams, protection settings |
| Cloud IAM users/roles, OIDC trust policies | Platform lead | IAM credential report, role list |
| Kubernetes RBAC | Platform lead | `kubectl get rolebindings,clusterrolebindings -A` |
| Database roles and grants | Data owner | `\du` and grants listing |
| Application admins | Product owner | `SELECT email FROM users WHERE role = 'admin'` + `admin.*` audit events |
| Third-party tools (Sentry, email provider, log platform) | Security lead | Member lists |

Remove access that is no longer needed, record the review (date, reviewer, changes) and keep the evidence for audits. Offboarding removes all access on the leaver's last day.
