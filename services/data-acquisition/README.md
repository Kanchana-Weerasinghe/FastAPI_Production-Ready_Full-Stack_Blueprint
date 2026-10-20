# data-acquisition

The **data acquisition** domain service. It owns acquisition jobs (what to collect, from which
source) and every rule about their lifecycle. Other applications use those rules only through this
service's HTTP API and, later, its domain events.

| | |
| :--- | :--- |
| Bounded context | Data acquisition |
| Aggregate | `AcquisitionJob` (`app/modules/acquisition_jobs/`) |
| API | `/v1/acquisition-jobs` ([openapi.json](openapi.json)) |
| Database | Shared PostgreSQL server, **own schema** `data_acquisition`, own roles ([roles](../../deploy/db/roles-data-acquisition.sql)) |
| Auth | `Authorization: Bearer <access token>` issued by the identity service, verified offline |
| Deploy unit | Own image ([Dockerfile](Dockerfile)), own Helm release ([chart](../../deploy/helm/domain-service)) |
| Shared code | [`platform-kit`](../../packages/platform-kit) (technical only, no business rules) |

## The AcquisitionJob aggregate

```
QUEUED --start--> RUNNING --complete--> COMPLETED
   |                 |
   |                 +--fail--> FAILED --retry--> QUEUED   (while attempts < maxAttempts)
   +-----cancel------+--cancel--> CANCELLED
```

| Aspect | Where | Examples |
| :--- | :--- | :--- |
| Properties | `domain/entities.py` | `name`, `source`, `status`, `attempts`, `maxAttempts`, `recordsCollected` |
| Value objects (validation) | `domain/value_objects.py` | `JobName` (3-120 chars), `DataSource` (web: http/https, api: https only, file: s3/sftp; no embedded credentials), `MaxAttempts` (1-10) |
| Behaviours | `domain/entities.py` | `start`, `record_progress`, `complete`, `fail`, `retry`, `cancel` |
| Invariants | entity methods | only valid transitions; progress > 0; retry only while attempts remain; failure needs a reason |
| Policy | `domain/policies.py` | an owner may have at most `ACTIVE_JOB_LIMIT_PER_OWNER` queued/running jobs |
| Domain events | `domain/events.py` | `AcquisitionJobQueued`, `…Completed`, `…Failed`, `…Cancelled` |
| Ports | `application/ports/` | `JobRepository`, `EventPublisher` |
| Use cases | `application/use_cases/` | `CreateJob`, `GetJob`, `ListJobs`, `CancelJob`, `RetryJob`, `StartJob`, `RecordProgress`, `CompleteJob`, `FailJob` |
| Adapters | `infrastructure/` | `SqlAlchemyJobRepository` (compare-and-set on `version`), `LoggingEventPublisher` |
| Authorization | use cases | owners/admins see and cancel/retry their jobs; only role `acquisition_worker` (or admin) reports lifecycle |
| Concurrency | repository + HTTP | `ETag: W/"<version>"`; `If-Match` on `:cancel`/`:retry` → 412 when stale |

## Endpoints

| Method | Path | Caller | Purpose |
| :--- | :--- | :--- | :--- |
| POST | `/v1/acquisition-jobs/` | owner | Queue a job (201, `Location`, `ETag`) |
| GET | `/v1/acquisition-jobs/` | owner (admin: `allOwners=true`) | List, filter by `status`, paginate (`page`, `pageSize` ≤ 100) |
| GET | `/v1/acquisition-jobs/{id}` | owner/admin | Get one job |
| POST | `/v1/acquisition-jobs/{id}:cancel` | owner/admin | Cancel a queued/running job |
| POST | `/v1/acquisition-jobs/{id}:retry` | owner/admin | Re-queue a failed job |
| POST | `/v1/acquisition-jobs/{id}:start` | worker | Mark running (counts an attempt) |
| POST | `/v1/acquisition-jobs/{id}:progress` | worker | Add collected records `{ "records": 250 }` |
| POST | `/v1/acquisition-jobs/{id}:complete` | worker | Mark completed |
| POST | `/v1/acquisition-jobs/{id}:fail` | worker | Mark failed `{ "reason": "..." }` |

Errors are RFC 9457 Problem Details with stable codes, e.g. `invalid_source`, `invalid_status_transition`,
`retry_limit_reached`, `active_job_limit_reached`, `acquisition_job_not_found`.

## Commands (from this folder)

```powershell
uv sync                       # installs platform-kit from ../../packages as an editable path dependency
uv run task upgrade           # migrate the data_acquisition schema
uv run task dev               # http://localhost:8010/docs
uv run task check; uv run task type-check
uv run task test              # unit + architecture + integration (needs Docker for Testcontainers)
uv run task openapi           # export openapi.json (commit it)
```

Image (built from the repository root so `platform-kit` is in the context):

```powershell
docker build -f services/data-acquisition/Dockerfile -t data-acquisition .
```

## Adding to this service

- **New aggregate in this domain** (e.g. `DataSource`): add `app/modules/<name>/` with the same layers,
  wire it in `app/container.py`, mount the router in `app/api.py`, register models in `app/models.py`,
  then `uv run alembic revision --autogenerate -m "..."` and review the migration.
- **Need data from another domain**: define a port in `application/ports/`, implement it in
  `infrastructure/` with `platform_kit.http.client.ServiceClient` (forwards the caller's token and request
  ID), and bind it in `container.py`. Never read another service's schema.
- **Other domains need to react to job events**: replace `LoggingEventPublisher` with an outbox +
  message-broker adapter; the use cases do not change.
