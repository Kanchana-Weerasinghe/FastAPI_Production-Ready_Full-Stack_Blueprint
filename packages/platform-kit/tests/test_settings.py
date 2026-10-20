import pytest
from pydantic import ValidationError

from platform_kit.settings import ServiceSettings


def test_development_allows_defaults() -> None:
    settings = ServiceSettings(ENVIRONMENT="development")
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_deployed_environment_rejects_insecure_defaults() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        ServiceSettings(ENVIRONMENT="production")


def test_deployed_environment_accepts_real_values() -> None:
    settings = ServiceSettings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-real-random-secret-key-of-at-least-32-chars",
        DB_PASSWORD="a-real-password",
        PROBLEM_TYPE_BASE_URI="https://errors.mycompany.com",
    )
    assert settings.is_deployed
