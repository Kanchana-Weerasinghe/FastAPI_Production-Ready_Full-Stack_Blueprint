"""
Base settings every domain service extends.

Settings are read from the environment (and a local `.env`). Deployed environments fail closed:
startup is refused while an insecure default secret or placeholder is still configured.
"""

from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "dev-insecure-secret-key-change-me"
INSECURE_DB_PASSWORD = "password"
MIN_SECRET_KEY_LENGTH = 32

Environment = Literal["development", "test", "staging", "production"]


class ServiceSettings(BaseSettings):
    """Configuration shared by all domain services; each service subclasses it and adds its own fields."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SERVICE_NAME: str = "service"
    APP_VERSION: str = "0.0.0-dev"
    ENVIRONMENT: Environment = "development"
    LOG_LEVEL: str = "INFO"

    # --- Database: one schema per service, accessed with the service's own role ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USERNAME: str = "root"
    DB_PASSWORD: SecretStr = SecretStr(INSECURE_DB_PASSWORD)
    DB_SCHEMA: str = "public"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_STATEMENT_TIMEOUT_MS: int = 15000

    # --- Token verification: access tokens are issued by the identity service ---
    # Shared HS256 secret today; move to asymmetric keys + JWKS when more services trust the issuer.
    JWT_SECRET_KEY: SecretStr = SecretStr(INSECURE_SECRET_KEY)
    JWT_ALGORITHM: str = "HS256"

    # --- HTTP ---
    MAX_REQUEST_BODY_BYTES: int = 1_048_576
    PROBLEM_TYPE_BASE_URI: str = "https://errors.example.com"
    CORS_ORIGINS: list[str] = []
    OUTBOUND_HTTP_TIMEOUT_SECONDS: float = 5.0

    @property
    def database_url(self) -> str:
        password = self.DB_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.DB_USERNAME}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def is_deployed(self) -> bool:
        return self.ENVIRONMENT in ("staging", "production")

    @model_validator(mode="after")
    def _fail_closed_when_deployed(self) -> "ServiceSettings":
        if not self.is_deployed:
            return self
        errors = []
        secret = self.JWT_SECRET_KEY.get_secret_value()
        if secret == INSECURE_SECRET_KEY or len(secret) < MIN_SECRET_KEY_LENGTH:
            errors.append(f"JWT_SECRET_KEY must be set to a random value of at least {MIN_SECRET_KEY_LENGTH} chars")
        if self.DB_PASSWORD.get_secret_value() == INSECURE_DB_PASSWORD:
            errors.append("DB_PASSWORD must not use the development default")
        if "example.com" in self.PROBLEM_TYPE_BASE_URI:
            errors.append("PROBLEM_TYPE_BASE_URI must point to your error documentation, not example.com")
        if errors:
            raise ValueError("Insecure configuration for a deployed environment: " + "; ".join(errors))
        return self
