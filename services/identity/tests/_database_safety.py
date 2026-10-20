from collections.abc import Mapping


def reject_external_test_database(environment: Mapping[str, str]) -> None:
    """Prevents schema-resetting tests from connecting to a shared or developer-managed database."""
    if environment.get("TEST_DB_HOST"):
        raise RuntimeError(
            "TEST_DB_HOST is not supported: tests recreate the schema and must use an isolated Testcontainers database."
        )
