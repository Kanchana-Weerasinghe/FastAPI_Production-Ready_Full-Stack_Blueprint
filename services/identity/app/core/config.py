import ipaddress
import warnings
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "dev-insecure-secret-key-change-me"
INSECURE_DB_PASSWORD = "password"
INSECURE_FIELD_ENCRYPTION_KEY = "dev-insecure-field-encryption-key"
MIN_SECRET_KEY_LENGTH = 32


class Configs(BaseSettings):
    """
    Global application settings managed via Pydantic BaseSettings.

    Loads configuration from environment variables and an optional .env file.
    Defaults are only safe for local development: outside `development` the app
    refuses to start with default secrets (fail closed).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DB_NAME: str = "postgres"
    DB_USERNAME: str = "root"
    DB_PASSWORD: SecretStr = SecretStr(INSECURE_DB_PASSWORD)
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_SCHEMA: str = "public"
    PROJECT_NAME: str = "FastAPI Template"
    # Release identifier (semver or git SHA), injected by CI at build time; tags errors, traces and logs.
    APP_VERSION: str = "0.0.0-dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Observability ---
    SENTRY_DSN: SecretStr | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    # OpenTelemetry tracing; exporter settings come from the standard OTEL_EXPORTER_OTLP_* variables.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "api"
    # Head sampling ratio for new traces (parent decisions are respected). Keep well below 1.0 in production.
    OTEL_TRACES_SAMPLE_RATIO: float = 0.1
    METRICS_ENABLED: bool = True
    # If set, /metrics requires "Authorization: Bearer <token>" (otherwise restrict it at the network level).
    METRICS_TOKEN: SecretStr | None = None
    # Base of the RFC 9457 `type` URI for error responses (`<base>/<code>`); point it at your error docs.
    PROBLEM_TYPE_BASE_URI: str = "https://errors.example.com"
    API: str = "/api"

    SQLALCHEMY_ECHO: bool = False
    # Pool per process. Total connections = replicas x gunicorn workers x (pool size + overflow) (+ worker);
    # keep it below Postgres max_connections, or put PgBouncer in front for many replicas.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 10
    # Set true behind PgBouncer in transaction-pooling mode (disables asyncpg prepared-statement caches).
    DB_PGBOUNCER: bool = False
    # Server-side guard: Postgres cancels statements running longer than this (0 = no limit).
    DB_STATEMENT_TIMEOUT_MS: int = 30000
    # Performance budget: statements slower than this are logged as `slow_query` warnings.
    DB_SLOW_QUERY_MS: int = 500
    # Optional separate (more privileged) role for Alembic; the app itself uses DB_USERNAME (DML only).
    MIGRATION_DB_USERNAME: str | None = None
    MIGRATION_DB_PASSWORD: SecretStr | None = None
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: SecretStr = SecretStr(INSECURE_SECRET_KEY)
    # Key for field-level encryption of secrets at rest (e.g. MFA seeds). Rotate by re-encrypting.
    FIELD_ENCRYPTION_KEY: SecretStr = SecretStr(INSECURE_FIELD_ENCRYPTION_KEY)

    # --- Sessions: short-lived access JWT + rotating opaque refresh token (see docs/adr/0008) ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MFA_CHALLENGE_EXPIRE_MINUTES: int = 5
    AUTH_COOKIE_NAME: str = "x-path-token"
    REFRESH_COOKIE_NAME: str = "x-refresh-token"
    # Refresh cookie is only sent to the auth endpoints, never to the rest of the API.
    REFRESH_COOKIE_PATH: str = "/v1/auth"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # --- Account protection & lifecycle ---
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    REQUIRE_VERIFIED_EMAIL: bool = False
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    # Public URL of the web app, used to build links in emails (verify email, reset password).
    FRONTEND_URL: str = "http://localhost:3000"
    # None = derive from ENVIRONMENT (Secure everywhere except development).
    AUTH_COOKIE_SECURE_OVERRIDE: bool | None = None
    APP_DOMAIN: str = "localhost"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Rate limiting. Use a shared backend (e.g. redis://host:6379) when running more than one worker.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    # Comma-separated IPs/CIDRs of reverse proxies allowed to set X-Forwarded-For / X-Real-IP.
    TRUSTED_PROXIES: str = ""

    AUTOSEND_API_KEY: SecretStr = SecretStr("test_key")
    AUTOSEND_FROM_EMAIL: str = "welcome@yourcompany.com"
    AUTOSEND_FROM_NAME: str = "Boost"
    AUTOSEND_URL: str = "https://api.autosend.com/v1/mails/send"

    # --- Redis / background jobs ---
    # Used by the ARQ worker (job queue + outbox relay) and checked by the readiness probe when set.
    REDIS_URL: str | None = None
    # Outbox: events are written in the request transaction and delivered by the worker.
    # None = deliver in-process right after commit in development (no worker needed), via the worker elsewhere.
    OUTBOX_INLINE_DISPATCH: bool | None = None
    OUTBOX_MAX_ATTEMPTS: int = 8
    OUTBOX_BATCH_SIZE: int = 100

    # --- Outbound HTTP resilience ---
    HTTP_TIMEOUT_SECONDS: float = 10.0
    HTTP_MAX_RETRIES: int = 3
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_SECONDS: float = 30.0

    # --- File storage: "local" (single instance / dev) or "s3" (S3, MinIO, R2, ...) ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    S3_BUCKET: str = ""
    S3_REGION: str | None = None
    # Set for S3-compatible services (MinIO, R2); leave empty for AWS.
    S3_ENDPOINT_URL: str | None = None
    # Leave empty to use the default AWS credential chain (IAM role / IRSA / env).
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: SecretStr | None = None
    S3_PRESIGNED_URL_EXPIRE_SECONDS: int = 300

    # Data retention (see docs/governance/data-retention.md); enforced by the worker.
    AUDIT_LOG_RETENTION_DAYS: int = 400

    # Idempotency-Key records are kept this long (retries after that execute again).
    IDEMPOTENCY_TTL_HOURS: int = 24

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    # Upper bound for any request body (upload + multipart overhead).
    MAX_REQUEST_BODY_BYTES: int = 11 * 1024 * 1024
    ORDERING: str = "-created_at"
    PAGE: int = 1
    PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
    DATE_FORMAT: str = "%Y-%m-%d"
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        ".pdf",
        ".xls",
        ".xlsx",
        ".docx",
        ".pptx",
        ".doc",
        ".ppt",
        ".json",
    ]

    @model_validator(mode="after")
    def validate_deployed_settings(self) -> Self:
        """Fails fast when a deployed environment (staging/production) still uses insecure defaults."""
        if self.ENVIRONMENT == "development":
            return self
        errors = []
        secret_key = self.SECRET_KEY.get_secret_value()
        if secret_key == INSECURE_SECRET_KEY or len(secret_key) < MIN_SECRET_KEY_LENGTH:
            errors.append(f"SECRET_KEY must be set to a random value of at least {MIN_SECRET_KEY_LENGTH} characters")
        encryption_key = self.FIELD_ENCRYPTION_KEY.get_secret_value()
        if encryption_key == INSECURE_FIELD_ENCRYPTION_KEY or len(encryption_key) < MIN_SECRET_KEY_LENGTH:
            errors.append(
                f"FIELD_ENCRYPTION_KEY must be set to a random value of at least {MIN_SECRET_KEY_LENGTH} characters"
            )
        if self.DB_PASSWORD.get_secret_value() == INSECURE_DB_PASSWORD:
            errors.append("DB_PASSWORD must not use the default value")
        if "*" in self.ALLOWED_ORIGINS:
            errors.append("CORS_ORIGINS must not contain '*' when credentials are allowed")
        if self.ENVIRONMENT == "production" and not self.AUTH_COOKIE_SECURE:
            errors.append("AUTH_COOKIE_SECURE_OVERRIDE must not disable Secure cookies in production")
        if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET:
            errors.append("S3_BUCKET is required when STORAGE_BACKEND=s3")
        if errors:
            raise ValueError(f"Insecure configuration for ENVIRONMENT={self.ENVIRONMENT}: " + "; ".join(errors))
        if self.ENVIRONMENT == "production" and self.RATE_LIMIT_ENABLED and self.RATE_LIMIT_STORAGE_URI == "memory://":
            warnings.warn(
                "RATE_LIMIT_STORAGE_URI is in-memory: limits are per worker process and not shared across instances",
                stacklevel=2,
            )
        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def MIGRATION_DATABASE_URI(self) -> str:
        """Connection used by Alembic: the migration role when configured, else the app role."""
        if not self.MIGRATION_DB_USERNAME:
            return self.SQLALCHEMY_DATABASE_URI
        password = self.MIGRATION_DB_PASSWORD.get_secret_value() if self.MIGRATION_DB_PASSWORD else ""
        return (
            f"postgresql+asyncpg://{self.MIGRATION_DB_USERNAME}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def TRUSTED_PROXY_NETWORKS(self) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        return [
            ipaddress.ip_network(proxy.strip(), strict=False)
            for proxy in self.TRUSTED_PROXIES.split(",")
            if proxy.strip()
        ]

    @property
    def OUTBOX_DISPATCH_INLINE(self) -> bool:
        if self.OUTBOX_INLINE_DISPATCH is not None:
            return self.OUTBOX_INLINE_DISPATCH
        return self.ENVIRONMENT == "development"

    @property
    def AUTH_COOKIE_SECURE(self) -> bool:
        if self.AUTH_COOKIE_SECURE_OVERRIDE is not None:
            return self.AUTH_COOKIE_SECURE_OVERRIDE
        return self.ENVIRONMENT != "development"


config = Configs()
