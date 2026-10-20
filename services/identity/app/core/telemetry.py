"""
Error tracking (Sentry) and distributed tracing (OpenTelemetry).

Both are opt-in via configuration so local development and tests need no collector:
- `SENTRY_DSN` enables Sentry, tagged with `APP_VERSION` (release) and `ENVIRONMENT`.
- `OTEL_ENABLED=true` enables tracing for incoming requests, SQL queries and outbound HTTP, exported
  over OTLP/HTTP (configure `OTEL_EXPORTER_OTLP_ENDPOINT`, e.g. an OpenTelemetry Collector).
  Traces are head-sampled (`OTEL_TRACES_SAMPLE_RATIO`), honouring the caller's sampling decision.
"""

from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from .config import config
from .logging import logger

_SCRUBBED_HEADERS = {"authorization", "cookie", "set-cookie", "x-csrf-token"}


def _scrub_event(event: Any, _hint: Any) -> Any:
    """Drops credentials from events before they leave the process."""
    request = event.get("request") or {}
    headers = request.get("headers") or {}
    for name in list(headers):
        if name.lower() in _SCRUBBED_HEADERS:
            headers[name] = "[REDACTED]"
    request.pop("cookies", None)
    request.pop("data", None)
    return event


def setup_sentry() -> None:
    if config.SENTRY_DSN is None:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=config.SENTRY_DSN.get_secret_value(),
        release=config.APP_VERSION,
        environment=config.ENVIRONMENT,
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_scrub_event,
    )
    logger.info("sentry_enabled", release=config.APP_VERSION)


def setup_tracing(app: FastAPI, engine: AsyncEngine) -> None:
    if not config.OTEL_ENABLED:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": config.OTEL_SERVICE_NAME,
                "service.version": config.APP_VERSION,
                "deployment.environment": config.ENVIRONMENT,
            }
        ),
        sampler=ParentBased(TraceIdRatioBased(config.OTEL_TRACES_SAMPLE_RATIO)),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/.*,metrics", tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    logger.info("tracing_enabled", sample_ratio=config.OTEL_TRACES_SAMPLE_RATIO)
