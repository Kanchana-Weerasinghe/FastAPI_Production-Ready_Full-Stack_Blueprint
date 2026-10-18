# 0008. Session tokens, revocation, CSRF and MFA

- Status: Accepted
- Date: 2026-10-16

## Context

Sessions were a single 7-day JWT in a cookie: a stolen cookie stayed valid for a week, there was no logout-everywhere, password changes did not end other sessions, there was no CSRF protection beyond `SameSite=Lax`, no brute-force protection per account, no email verification, password reset or MFA.

## Decision

- **Access token**: JWT, 15 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`), `HttpOnly` cookie on `/`. Claims: `sub`, `role`, `ver` (the user's `token_version`), `type`, `iat`, `exp`, `jti`. Every request compares `ver` with the database, so bumping `token_version` (password change/reset, sign-out everywhere) revokes all access tokens immediately.
- **Refresh token**: opaque 256-bit random value, 30 days (`REFRESH_TOKEN_EXPIRE_DAYS`), `HttpOnly` cookie scoped to `/v1/auth` so it is never sent to the rest of the API. Only its SHA-256 hash is stored (`refresh_tokens`). It **rotates** on every `/v1/auth/refresh`; tokens of one sign-in share a `family_id`, and presenting an already-rotated token revokes the family (theft detection, OAuth 2.0 Security BCP).
- **CSRF**: double-submit cookie. A random `csrf_token` cookie (readable by JS) must be echoed in `X-CSRF-Token` on unsafe methods whenever a session cookie is present (`CSRFMiddleware`). Session-establishing endpoints are exempt. Cookies stay `SameSite=Lax` and `Secure` outside development.
- **Brute force**: per-IP rate limits (ADR 0006) plus per-account lockout (`LOGIN_MAX_FAILED_ATTEMPTS` → `LOGIN_LOCKOUT_MINUTES`). The counter is persisted although the request fails (`UnitOfWork.persist_on_failure`). Unknown emails still run bcrypt against a dummy hash (constant time).
- **Email verification & password reset**: single-use, expiring tokens; only their hash is stored (`one_time_tokens`); issuing a new one invalidates older ones; reset revokes all sessions and notifies the user. `forgot` always answers 202 (no account enumeration). `REQUIRE_VERIFIED_EMAIL` can block sign-in for unverified accounts.
- **MFA**: TOTP (RFC 6238) via authenticator apps. The seed is encrypted at rest (`FIELD_ENCRYPTION_KEY`, Fernet). With MFA on, sign-in returns a 5-minute `mfa_challenge` token, exchanged with a code at `/v1/auth/mfa/verify`; wrong codes count towards lockout.
- **Identity provider (optional)**: the built-in auth is the default. To delegate to an OIDC provider (Keycloak, Auth0, Cognito, Entra ID), replace the `auth` module's sign-in with the OIDC authorization-code flow (with PKCE) and keep issuing the same first-party session cookies after the callback; the rest of the app depends only on `CurrentUserDep`/`require_permission`, so nothing else changes.

## Consequences

- One extra database read per request (token version check); cache it in Redis if it ever matters.
- The web client must send `X-CSRF-Token` (axios `xsrfCookieName`/`xsrfHeaderName`) and call `/v1/auth/refresh` on 401 (implemented in `web/src/lib/client.ts`).
- Not yet covered: TOTP replay within the same 30-second step, recovery codes, WebAuthn/passkeys, and a "list/revoke my sessions" UI (the `refresh_tokens` table already holds what it needs).
- Expired/revoked rows in `refresh_tokens` and `one_time_tokens` need periodic cleanup (scheduled job).
