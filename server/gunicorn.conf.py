"""Gunicorn settings shared by all deployments (CLI flags in scripts/start.sh override nothing here)."""

from typing import Any


def child_exit(_server: Any, worker: Any) -> None:
    """Drop a dead worker's live gauges from the Prometheus multiprocess directory."""
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)  # type: ignore[no-untyped-call]
