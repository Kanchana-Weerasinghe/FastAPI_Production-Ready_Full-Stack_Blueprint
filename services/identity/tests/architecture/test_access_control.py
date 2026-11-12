"""
Central access control (docs/adr/0017-central-access-control.md), enforced on every test run:
every API route has a stable operation_id and passes `require_access()`, and the access document only
grants operations this service has. The same check runs at startup (`install_access`).
"""

from platform_kit.access import access_setup_errors, load_access_policy, route_operation_ids

from app.core.config import config
from app.main import ACCESS_EXEMPT_PATH_PREFIXES, app


def test_every_route_is_access_controlled_and_the_document_matches_the_routes() -> None:
    policy = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    errors = access_setup_errors(app, policy=policy, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    assert not errors, "\n".join(errors)


def test_access_document_grants_every_route_to_some_role() -> None:
    """A route no role holds is unreachable; it is usually a forgotten grant in the access document."""
    policy = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    routes = route_operation_ids(app, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    assert not sorted(routes - policy.operations)
