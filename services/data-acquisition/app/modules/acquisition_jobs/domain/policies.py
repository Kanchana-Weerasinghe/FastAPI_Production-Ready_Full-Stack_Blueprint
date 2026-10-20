"""
Policies: business decisions that need facts the entity does not hold.

The use case fetches the facts (through ports) and passes them in; the policy stays a pure,
easily tested function. A database constraint or lock is still needed where races matter.
"""

from app.modules.acquisition_jobs.domain.exceptions import ActiveJobLimitReached


def ensure_owner_can_queue_job(*, active_jobs: int, limit: int) -> None:
    """An owner may have at most `limit` queued or running jobs, to share acquisition capacity fairly."""
    if active_jobs >= limit:
        raise ActiveJobLimitReached(f"You already have {active_jobs} active jobs (limit {limit})")
