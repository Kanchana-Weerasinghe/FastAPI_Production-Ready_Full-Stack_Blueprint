import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "br(rule_id, case_id): links a test to a business rule and test case")
