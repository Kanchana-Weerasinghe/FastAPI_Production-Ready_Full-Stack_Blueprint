"""Settings of the monitoring service: environment variables, then a local `.env`."""

from pathlib import Path

from platform_kit.settings import ServiceSettings

_SERVICE_DIR = Path(__file__).resolve().parents[2]


class Settings(ServiceSettings):
    SERVICE_NAME: str = "monitoring"
    DB_SCHEMA: str = "monitoring"
    # The central access document (config/access-control.json in the repository). The image sets
    # ACCESS_CONFIG_PATH=/app/config/access-control.json; mount a ConfigMap over it to change access.
    ACCESS_CONFIG_PATH: str = str(_SERVICE_DIR.parent.parent / "config" / "access-control.json")

    # --- Rate limiting: memory:// counts per process; use redis://... to share counters across replicas ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # --- Business configuration ---


config = Settings()
