# 0007. Fail-closed configuration outside development

- Status: Accepted
- Date: 2026-10-16

## Context

The app shipped with `SECRET_KEY="secret"` and default database credentials and would start in production with them, letting anyone forge session tokens.

## Decision

- Settings are typed (`pydantic-settings`), read from the environment (twelve-factor), and secrets are `SecretStr` so they never appear in logs or reprs.
- In `staging` and `production` the app refuses to start when `SECRET_KEY` or `FIELD_ENCRYPTION_KEY` is default or shorter than 32 characters, `DB_PASSWORD` is default, CORS allows `*` with credentials, or (production) Secure cookies are disabled.
- Defaults are only for local development. `.env` files are never committed; `.env.example` documents every variable. Docker Compose requires secrets via `${VAR:?}` interpolation.
- In deployed environments secrets come from a secrets manager (injected as environment variables by the platform), never from files in the image.

## Consequences

- Misconfigured deployments fail at startup instead of running insecurely.
- New secrets must be added to the validator and `.env.example`.
