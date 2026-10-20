from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import INSECURE_SECRET_KEY, Configs

STRONG_SECRET = "s" * 40


def _settings(**values: Any) -> Configs:
    """Builds settings from explicit values only, ignoring any local .env file."""
    return Configs(**{"_env_file": None, **values})


def _configs(**overrides: Any) -> Configs:
    values: dict[str, Any] = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": STRONG_SECRET,
        "FIELD_ENCRYPTION_KEY": STRONG_SECRET,
        "DB_PASSWORD": "strong-db-pass",
        "AUTH_COOKIE_SECURE_OVERRIDE": None,
        "RATE_LIMIT_ENABLED": True,
    }
    values.update(overrides)
    return _settings(**values)


def test_development_allows_insecure_defaults() -> None:
    """Test that development may start with the built-in defaults."""
    settings = _settings(ENVIRONMENT="development", SECRET_KEY=INSECURE_SECRET_KEY, DB_PASSWORD="password")
    assert settings.AUTH_COOKIE_SECURE is False


def test_production_with_secure_settings() -> None:
    """Test that production starts when secrets are set, and cookies default to Secure."""
    settings = _configs()
    assert settings.AUTH_COOKIE_SECURE is True
    assert "strong-db-pass" not in repr(settings)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"SECRET_KEY": INSECURE_SECRET_KEY}, "SECRET_KEY"),
        ({"SECRET_KEY": "too-short"}, "SECRET_KEY"),
        ({"DB_PASSWORD": "password"}, "DB_PASSWORD"),
        ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
        ({"AUTH_COOKIE_SECURE_OVERRIDE": False}, "Secure cookies"),
    ],
    ids=["default-secret", "short-secret", "default-db-password", "wildcard-cors", "insecure-cookie"],
)
def test_production_fails_closed(overrides: dict[str, Any], message: str) -> None:
    """Test that production refuses to start with insecure configuration values."""
    with pytest.raises(ValidationError, match=message):
        _configs(**overrides)


def test_staging_also_fails_closed() -> None:
    """Test that staging is held to the same secret requirements as production."""
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _configs(ENVIRONMENT="staging", SECRET_KEY=INSECURE_SECRET_KEY)


def test_staging_may_disable_secure_cookie() -> None:
    """Test that only production forbids disabling Secure cookies (staging may run over plain HTTP)."""
    assert _configs(ENVIRONMENT="staging", AUTH_COOKIE_SECURE_OVERRIDE=False).AUTH_COOKIE_SECURE is False


def test_production_warns_on_in_memory_rate_limit_storage() -> None:
    """Test that production warns when rate limits are kept in per-process memory."""
    with pytest.warns(UserWarning, match="RATE_LIMIT_STORAGE_URI"):
        _configs()


def test_trusted_proxy_networks_parsing() -> None:
    """Test that TRUSTED_PROXIES accepts a comma-separated list of IPs and CIDR ranges."""
    settings = _settings(TRUSTED_PROXIES="10.0.0.0/8, 127.0.0.1")
    assert [str(network) for network in settings.TRUSTED_PROXY_NETWORKS] == ["10.0.0.0/8", "127.0.0.1/32"]
