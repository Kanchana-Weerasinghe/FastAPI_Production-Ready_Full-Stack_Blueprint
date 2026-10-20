import pytest

from tests._database_safety import reject_external_test_database


def test_external_database_override_is_refused() -> None:
    """Test that destructive test setup refuses externally managed database connections."""
    with pytest.raises(RuntimeError, match="TEST_DB_HOST is not supported"):
        reject_external_test_database({"TEST_DB_HOST": "shared-database"})


def test_default_test_database_configuration_is_allowed() -> None:
    """Test that the isolated Testcontainers configuration is not blocked."""
    reject_external_test_database({})
