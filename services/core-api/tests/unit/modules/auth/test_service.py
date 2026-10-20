from app.modules.auth.permissions import Role, has_permission
from app.modules.auth.service import generate_username


def test_generate_username() -> None:
    """Test that generate_username creates an uppercase alphanumeric string of the requested length."""
    username = generate_username(10)
    assert len(username) == 10
    assert username.isalnum()
    assert username.upper() == username


def test_role_permissions() -> None:
    """Test that admins hold every permission and regular users hold none of the admin ones."""
    assert has_permission(Role.ADMIN, "users:read_all")
    assert not has_permission(Role.USER, "users:read_all")
    assert not has_permission("unknown-role", "users:read_all")
