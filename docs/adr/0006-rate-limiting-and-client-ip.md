# 0006. Shared rate-limit storage and trusted-proxy client IPs

- Status: Accepted
- Date: 2026-10-16

## Context

Rate limits were disabled in development and staging, stored in per-process memory (with 4 gunicorn workers a 10/minute login limit let ~40 attempts through), and keyed on `X-Forwarded-For`, which any client can forge to get a fresh limit per request.

## Decision

- Rate limiting is on by default in every environment (`RATE_LIMIT_ENABLED`), configured per endpoint with `rate_limit("N/period")`, strictest on auth (sign-in 10/min, sign-up 5/min per IP).
- Counters live in shared storage (`RATE_LIMIT_STORAGE_URI=redis://...`); production warns when it is left in memory.
- The client IP is the TCP peer unless the peer is in `TRUSTED_PROXIES`; only then is `X-Forwarded-For` walked right-to-left, skipping trusted hops.

## Consequences

- Behind a load balancer or CDN, `TRUSTED_PROXIES` must list its address ranges or every client shares the proxy's IP.
- Redis becomes a runtime dependency (also used for caching and the job queue in later phases).
- Per-account login throttling and lockout (beyond per-IP limits) are handled by the authentication hardening work.
