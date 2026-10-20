"""The service's declarative base: every table lives in this service's own schema."""

from platform_kit.persistence import schema_metadata
from sqlalchemy.orm import DeclarativeBase

from app.config import config


class Base(DeclarativeBase):
    metadata = schema_metadata(config.DB_SCHEMA)
