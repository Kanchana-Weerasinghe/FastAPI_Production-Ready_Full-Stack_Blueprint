"""
Prometheus metrics.

RED for the HTTP API (Rate, Errors, Duration) recorded by `CoreMiddleware`, labelled by route
*template* (never the raw path, which would explode cardinality), plus USE-style gauges for
saturation (DB pool in use) and the outbox backlog, refreshed when `/metrics` is scraped.

With several gunicorn workers set `PROMETHEUS_MULTIPROC_DIR` (done by `scripts/start.sh`) so all
workers' metrics are aggregated in one scrape.
"""

import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP requests by route template, method and status code", ["method", "route", "status"]
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency by route template and method",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
DB_POOL_IN_USE = Gauge("db_pool_connections_in_use", "Checked-out DB connections", multiprocess_mode="livesum")
DB_POOL_SIZE = Gauge("db_pool_size", "Configured DB pool size", multiprocess_mode="livesum")
OUTBOX_PENDING = Gauge("outbox_pending_events", "Outbox events waiting for delivery", multiprocess_mode="max")
OUTBOX_DEAD = Gauge("outbox_dead_events", "Outbox events in the dead-letter state", multiprocess_mode="max")
OUTBOX_OLDEST_PENDING = Gauge(
    "outbox_oldest_pending_age_seconds", "Age of the oldest pending outbox event", multiprocess_mode="max"
)


def record_request(method: str, route: str, status: int, duration: float) -> None:
    HTTP_REQUESTS.labels(method=method, route=route, status=str(status)).inc()
    HTTP_DURATION.labels(method=method, route=route).observe(duration)


def render_latest() -> tuple[bytes, str]:
    """Serialises all metrics, aggregating worker processes in multiprocess mode."""
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST
