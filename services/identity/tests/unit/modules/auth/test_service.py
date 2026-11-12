from platform_kit.access import AccessSubject, load_access_policy

from app.core.config import config
from app.modules.auth.public import generate_username
from app.modules.users.domain.value_objects import Role


def test_generate_username() -> None:
    """Test that generate_username creates an uppercase alphanumeric string of the requested length."""
    username = generate_username(10)
    assert len(username) == 10
    assert username.isalnum()
    assert username.upper() == username


def test_role_access_comes_from_the_access_document() -> None:
    """Test that the access document lets admins list users and read the audit log, and nobody else."""
    policy = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    admin = policy.operations_for(AccessSubject.signed_in({Role.ADMIN}))
    user = policy.operations_for(AccessSubject.signed_in({Role.USER}))
    unknown = policy.operations_for(AccessSubject.signed_in({"unknown-role"}))
    assert {"listUsers", "listAuditLogs"} <= admin
    assert not {"listUsers", "listAuditLogs"} & user
    assert not {"listUsers", "listAuditLogs"} & unknown
    assert {"getCurrentUser", "changePassword"} <= user
