"""Structured JSON logging with request context and secret redaction."""

import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

_SENSITIVE_KEY = re.compile(r"pass(word)?|secret|token|authorization|cookie|api[_-]?key|credential", re.IGNORECASE)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REDACTED = "[REDACTED]"

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: REDACTED if _SENSITIVE_KEY.search(str(k)) else _redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_redact(v) for v in value)
    if isinstance(value, str):
        return _EMAIL.sub("[EMAIL]", value)
    return value


def redact_sensitive(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Removes secrets and masks email addresses (PII) before a log line is rendered."""
    for key in list(event_dict):
        if key != "event":
            event_dict[key] = REDACTED if _SENSITIVE_KEY.search(key) else _redact(event_dict[key])
    return event_dict


def setup_logging(*, service: str, version: str, environment: str, level: str = "INFO") -> None:
    """One JSON object per line on stdout; human-readable output in development."""

    def add_service(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", service)
        event_dict.setdefault("version", version)
        event_dict.setdefault("env", environment)
        return event_dict

    renderer: Any = (
        structlog.dev.ConsoleRenderer() if environment == "development" else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_service,
            redact_sensitive,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
