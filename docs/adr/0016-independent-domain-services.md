# 0016. Independent domain services with a shared platform kit

- Status: Accepted
- Date: 2026-10-20
- Amends: [0001](0001-modular-monolith.md) (the monolith becomes `core-api`, one service among several)

## Context

The product will grow into several business domains owned by different teams, starting with data
acquisition. Each domain must be developed, tested, versioned and deployed on its own, while its business
rules stay in one place and other applications consume them only through an API.

A single modular monolith couples every domain's release, and copying `core/` and `shared/` into every new
service would create several diverging copies of the same infrastructure code.

## Decision

- **One service per bounded context** under `services/<name>-api/`. Each has its own image, Helm release
  (`deploy/helm/domain-service`), migrations, tests, OpenAPI contract and version. The existing application
  is `services/core-api/` (identity, users, audit and the todos example).
- **Business rules live only in the owning service**, in its `domain/` and `application/` layers (entities,
  value objects, policies, use cases, ports). Other applications call its HTTP API or, later, consume its
  domain events. No service imports another service's code.
- **One PostgreSQL server, one schema per service** with its own owner and runtime roles
  (e.g. `deploy/db/roles-data-acquisition.sql`). Other services' data is referenced by ID only: no
  cross-schema foreign keys, joins or reads.
- **core-api is the identity provider.** Domain services verify its short-lived access tokens offline
  (`platform_kit.auth`) and accept them only as `Authorization: Bearer`. Cookies and CSRF stay at the
  browser edge (core-api, BFFs, gateway). Calls between services forward the caller's token and
  `X-Request-ID` (`platform_kit.http.client.ServiceClient`).
- **`packages/platform-kit`** holds the technical building blocks: settings, logging, unit of work, RFC 9457
  errors, request middleware, health, token verification, ETag helpers, pagination and the
  service-to-service HTTP client. It contains no business rules and is a versioned, editable path
  dependency of each new service.
- **Domain events** are recorded by aggregates and published through an `EventPublisher` port after
  commit. The first adapter logs them; an outbox plus message broker replaces it when another domain
  needs to react, without changing the use cases.

## Consequences

- Teams can ship a domain without coordinating releases. In return, each service needs its own pipeline,
  monitoring and on-call ownership.
- Cross-domain consistency is eventual: use events, sagas or idempotent retries instead of shared
  transactions.
- Token revocation reaches domain services only at access-token expiry (15 minutes). Move to asymmetric
  signing keys with a JWKS endpoint before many services trust core-api, so they do not share a secret.
- core-api still has its own copy of the infrastructure code. Migrate it to `platform-kit` incrementally;
  until then, fixes to shared concerns must be applied in both places.
- An API gateway (routing `/v1/acquisition-jobs` → data-acquisition-api, `/v1/auth`, `/v2/...` → core-api)
  and the message broker are the next platform pieces; neither exists yet.
