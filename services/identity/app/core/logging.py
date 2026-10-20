import logging
import re
import sys
from typing import Any

import structlog
from opentelemetry import trace
from structlog.types import EventDict, Processor, WrappedLogger

from app.core.config import config

# Keys whose values must never reach logs (credentials, tokens, secrets, raw personal data).
_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|authorization|cookie|api[_-]?key|session|otp|mfa_code|credit|card|ssn",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REDACTED = "[REDACTED]"


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
        if key == "event":
            continue
        event_dict[key] = REDACTED if _SENSITIVE_KEY.search(key) else _redact(event_dict[key])
    return event_dict


def add_trace_context(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Adds OpenTelemetry trace/span ids so logs can be joined with traces."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def add_service_context(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("service", config.OTEL_SERVICE_NAME)
    event_dict.setdefault("version", config.APP_VERSION)
    event_dict.setdefault("env", config.ENVIRONMENT)
    return event_dict


def setup_logging() -> None:
    """
    Configures structured logging with structlog.

    Production: one JSON object per line on stdout (request_id, trace_id, service, version, env),
    secrets redacted and emails masked. Development on a TTY: human-readable console output.
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context,
        add_trace_context,
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        redact_sensitive,
        structlog.processors.UnicodeDecoder(),
    ]

    if config.ENVIRONMENT == "development" and sys.stderr.isatty():
        processors.append(structlog.processors.StackInfoRenderer())
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(config.LOG_LEVEL)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=config.LOG_LEVEL,
    )


logger = structlog.get_logger()
