from app.modules.flags.domain.policies import is_flag_enabled, rollout_bucket


def test_rollout_bucket_is_stable_and_in_range() -> None:
    """Verify the same flag/user pair consistently maps to a percentage bucket."""
    assert rollout_bucket("new-dashboard", "user-1") == rollout_bucket("new-dashboard", "user-1")
    assert 0 <= rollout_bucket("new-dashboard", "user-1") < 100


def test_flag_policy_honors_targeted_roles_and_percentage() -> None:
    """Verify feature evaluation combines enabled, role, and rollout rules."""
    assert is_flag_enabled(
        key="beta",
        enabled=True,
        rollout_percentage=0,
        roles=["admin"],
        user_id=None,
        role="admin",
    )
    assert not is_flag_enabled(
        key="beta",
        enabled=True,
        rollout_percentage=0,
        roles=["admin"],
        user_id=None,
        role="user",
    )
    assert not is_flag_enabled(
        key="beta",
        enabled=False,
        rollout_percentage=100,
        roles=[],
        user_id="user-1",
        role=None,
    )
