from platform_kit.http.app import create_service_app
from platform_kit.logging import setup_logging

from app.api import API_ROUTERS
from app.config import config
from app.container import Container

setup_logging(
    service=config.SERVICE_NAME, version=config.APP_VERSION, environment=config.ENVIRONMENT, level=config.LOG_LEVEL
)

container = Container()

app = create_service_app(
    settings=config,
    db=container.db(),
    routers=API_ROUTERS,
    title="Data Acquisition API",
    description="Owns acquisition jobs: what to collect, from which source, and the job lifecycle rules.",
)
app.state.container = container
