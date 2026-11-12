from fastapi import Request
from fastapi.responses import JSONResponse
from platform_kit.access import JsonFileAccessLookup, install_access
from platform_kit.http.app import create_service_app
from platform_kit.http.problems import problem_response
from platform_kit.logging import setup_logging
from slowapi.errors import RateLimitExceeded

from app.api import API_ROUTERS
from app.container import Container
from app.core.config import config
from app.core.security import limiter
from app.modules.auth.dependencies import get_access_subject

# Routes outside access control (probes and the development-only docs). Every other route must carry
# an operation_id and pass `require_access()`; the service refuses to start otherwise.
ACCESS_EXEMPT_PATH_PREFIXES = ("/health", "/docs")

setup_logging(
    service=config.SERVICE_NAME, version=config.APP_VERSION, environment=config.ENVIRONMENT, level=config.LOG_LEVEL
)

container = Container()
db = container.db()

app = create_service_app(
    settings=config,
    db=db,
    routers=API_ROUTERS,
    title="Monitoring API",
    description="The Monitoring domain service.",
)
app.state.container = container
app.state.limiter = limiter


async def _rate_limited(request: Request, _exc: Exception) -> JSONResponse:
    return problem_response(
        request,
        base_uri=config.PROBLEM_TYPE_BASE_URI,
        status=429,
        code="rate_limited",
        title="Too Many Requests",
        detail="Too many requests. Please try again later.",
    )


app.add_exception_handler(RateLimitExceeded, _rate_limited)

# Central access control: who may call which operation is data in config/access-control.json.
install_access(
    app,
    subject=get_access_subject,
    lookup=JsonFileAccessLookup(
        config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME, reload_seconds=config.ACCESS_RELOAD_SECONDS
    ),
    exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES,
)
