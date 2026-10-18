# Deployment

## Environments

| Environment | Purpose | Infrastructure | Deploys |
| :--- | :--- | :--- | :--- |
| Local | Development | `uv run task dev` + `pnpm dev` (or `docker compose up`) | – |
| Staging | Pre-production, same topology as production at smaller size | `deploy/terraform/aws` (`envs/staging.tfvars`) + Helm `values-staging.yaml` | Every merge to `main` |
| Production | Users | `envs/production.tfvars` + `values-production.yaml` | After approval, same image digests as staging |

Parity rules: same images, same chart, same migrations, same kind of managed services (Postgres, Redis, S3); only sizes, hosts and secrets differ.

## Prerequisites and first deployment

The Terraform folder provisions the AWS VPC, managed database/cache, upload bucket and application
secret. The Kubernetes cluster, DNS, ingress controller, cert-manager, External Secrets Operator,
Prometheus Operator and workload IAM roles are platform prerequisites; they are intentionally not
created by this application stack.

Terraform state must be stored in a bucket and lock table created separately by the platform team.
The backend is deliberately partial so the repository contains no pretend state bucket:

```sh
cd deploy/terraform/aws
terraform init \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="key=app/$ENVIRONMENT.tfstate" \
  -backend-config="region=$AWS_REGION" \
  -backend-config="dynamodb_table=$TF_LOCK_TABLE" \
  -backend-config="encrypt=true"
terraform plan -var-file="envs/$ENVIRONMENT.tfvars" \
  -var='app_security_group_ids=["sg-0123456789abcdef0"]'
```

Use distinct state keys per environment and least-privilege AWS credentials from the AWS credential
chain. `app_security_group_ids` is required: supply the private workload security groups that must
reach Postgres and Redis. Apply reviewed plans only. Set the GitHub `staging` and `production`
environment variables `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `EKS_CLUSTER`, `APP_URL`, `APP_DOMAIN`
and `S3_BUCKET`. `APP_DOMAIN` and `S3_BUCKET` must be real environment-specific values; the release
workflow rejects missing/example values and passes them, along with the repository's image names,
to Helm. Populate the referenced Kubernetes Secret from Secrets Manager via External Secrets before
deploying. The migration job must use a migration-only DB role; replace the initial Terraform
bootstrap DB credential with the least-privilege runtime and migration roles described in
[`../../deploy/db/roles.sql`](../../deploy/db/roles.sql).

Do not install the chart with its sample values unchanged. Helm intentionally fails while example
image repositories, domains, or upload-bucket names remain. The release workflow supplies those
inputs; a manual installation must provide real `image.api.repository`, `image.web.repository`,
`config.APP_DOMAIN`, `config.CORS_ORIGINS`, `config.FRONTEND_URL`, `config.S3_BUCKET`, and matching
`ingress.host` values.

### Database connection budget

Each API/worker process has its own SQLAlchemy pool. Before changing autoscaling or pool settings,
budget the maximum number of possible database connections:

```text
API max replicas × WEB_CONCURRENCY × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
+ worker max replicas × worker process count × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
+ migration/maintenance/administrative headroom
```

Keep that total below the database's usable connection limit, reserving capacity for failover and
operations. If the application needs more replicas than the database can support, reduce per-process
pools or put a correctly configured PgBouncer in transaction mode in front of Postgres.

## Pipeline (`.github/workflows/ci.yml` → `release.yml`)

1. **Pull request**: lint, types, unit + integration tests with coverage gate, architecture rules, migrations round-trip, OpenAPI contract up to date + breaking-change diff, generated client up to date, dependency audit (pip-audit, pnpm audit), SAST (Bandit), secret scan (gitleaks), Helm/Terraform validation, browser E2E against a disposable local stack, image build + Trivy.
2. **Merge to `main`**: build each image **once** (tag = commit SHA), Trivy scan, SBOM + provenance attestations, keyless cosign signature.
3. **Staging**: `helm upgrade --atomic` with the image **digests**. The migration Job runs first (pre-upgrade hook); any failure rolls the release back. Smoke tests run against the public URL.
4. **Production**: protected GitHub environment (manual approval). Signatures are verified, then the **same digests** are deployed the same way.
5. **Versioning**: release-please maintains a release PR from Conventional Commits; merging it tags `vX.Y.Z` and updates `CHANGELOG.md`.

The CI E2E job starts only the Compose database, Redis, migration and API services; it does not start
the background worker or call the configured email provider. Its database volume is removed after
the run. Backend pytest similarly requires Docker/Testcontainers and refuses `TEST_DB_HOST`, because
the session fixture drops and recreates the schema.

## Rollback

- Automatic: `helm upgrade --atomic` reverts on failed rollout/probes.
- Manual: `helm rollback app <revision> -n app` (redeploys the previous digests). Because migrations are backward compatible (expand/contract), the previous version runs against the newer schema.
- Data: see [disaster-recovery.md](disaster-recovery.md).

## Progressive delivery

The chart does rolling updates with `maxUnavailable: 0`. For canary or blue/green, add Argo Rollouts (replace the API `Deployment` with a `Rollout` and gate promotion on the SLO metrics in `deploy/observability/alerts.yml`) or use your ingress controller's canary annotations. Risky features ship dark behind feature flags (see `docs/adr`), independent of deploys.

## Secrets

Terraform creates secrets in AWS Secrets Manager → External Secrets Operator syncs them into the Kubernetes Secret referenced by `existingSecret` → pods read them as environment variables. Nothing secret lives in Git, images or Helm values. Rotate in Secrets Manager; restart pods (`kubectl rollout restart`) to pick up new values.

## Network

- Public subnets contain only load balancers; workloads, Postgres and Redis live in private subnets, reachable only from the application security groups.
- Put a WAF (AWS WAF / Cloudflare) in front of the load balancer with managed rule sets and rate-based rules.
- `/metrics` and `/health/*` are not routed by the ingress; NetworkPolicies restrict pod-to-pod traffic.
- No database admin UIs are deployed; use SSM Session Manager / a bastion with audited access for break-glass operations.

## GitOps (optional)

Larger teams can switch from push-based `helm upgrade` to Argo CD (`deploy/argocd/application.yaml`): CI only builds and signs images and opens a PR bumping the digests in `values-<env>.yaml`.
