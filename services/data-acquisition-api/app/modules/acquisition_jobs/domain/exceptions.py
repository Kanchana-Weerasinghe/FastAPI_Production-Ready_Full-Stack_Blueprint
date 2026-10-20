"""
Named business errors of the acquisition-jobs domain.

They extend the framework-agnostic `platform_kit.errors` types, so each rule violation has a stable
`code` and maps to an RFC 9457 response without the domain knowing about HTTP.
"""

from platform_kit.errors import ConflictError, NotFoundError, UnprocessableError


class InvalidJobName(UnprocessableError):
    code = "invalid_job_name"


class InvalidSource(UnprocessableError):
    code = "invalid_source"


class InvalidMaxAttempts(UnprocessableError):
    code = "invalid_max_attempts"


class InvalidProgress(UnprocessableError):
    code = "invalid_progress"


class InvalidFailureReason(UnprocessableError):
    code = "invalid_failure_reason"


class InvalidStatusTransition(ConflictError):
    code = "invalid_status_transition"


class RetryLimitReached(ConflictError):
    code = "retry_limit_reached"


class ActiveJobLimitReached(ConflictError):
    code = "active_job_limit_reached"


class JobNotFound(NotFoundError):
    code = "acquisition_job_not_found"

    def __init__(self) -> None:
        super().__init__("Acquisition job not found")


class ConcurrentModification(ConflictError):
    code = "concurrent_modification"

    def __init__(self) -> None:
        super().__init__("The job was changed by another request; reload it and retry")
