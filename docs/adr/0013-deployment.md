# 0013. Containers on Kubernetes, infrastructure as code, build once and promote

- Status: Accepted
- Date: 2026-10-16

## Context

The template ran as a single-node Docker Compose stack: a root-owned image that migrated the database on every start, a published database port, no environments, no infrastructure as code and no release process.

## Decision

- **Images**: multi-stage, slim base, non-root fixed UID, read-only root filesystem compatible, no build tools at runtime; the same API image runs the API, the worker and the migration job. Base images are pinned and kept current by Dependabot.
- **Orchestration**: Kubernetes via the Helm chart in `deploy/helm/app` (probes, resources, HPA, PDB, topology spread, NetworkPolicies, security contexts, pre-upgrade migration Job). Docker Compose remains for local and single-host use only.
- **Infrastructure as code**: Terraform (`deploy/terraform/aws`): private networking, managed Postgres with multi-AZ and PITR, Redis with encryption, a private versioned S3 bucket, and Secrets Manager. No hand-configured servers. AWS is the reference; the same shape maps to GCP/Azure.
- **Delivery**: build once per commit, scan, attest, sign, promote the same digests staging → production with an approval gate; atomic Helm upgrades for automatic rollback; migrations as a separate gated step; release-please for semantic versions and changelogs.
- **GitOps** with Argo CD is the documented option for larger teams.

## Consequences

- Teams need a Kubernetes cluster (EKS/GKE/AKS) and the External Secrets Operator; the platform stack (cluster, DNS, WAF, CDN) is outside this template.
- `values-*.yaml` and `*.tfvars` contain placeholders (`example.com`, `your-org`) that must be replaced per project.
