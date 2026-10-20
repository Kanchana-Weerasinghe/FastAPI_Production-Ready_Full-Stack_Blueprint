from platform_kit.settings import ServiceSettings


class Settings(ServiceSettings):
    SERVICE_NAME: str = "data-acquisition"
    DB_SCHEMA: str = "data_acquisition"

    # --- Business configuration ---
    ACTIVE_JOB_LIMIT_PER_OWNER: int = 10
    DEFAULT_MAX_ATTEMPTS: int = 3


config = Settings()
