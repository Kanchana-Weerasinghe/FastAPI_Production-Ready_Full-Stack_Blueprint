"""Small immutable values that validate themselves; an invalid value can never be constructed."""

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from app.modules.acquisition_jobs.domain.exceptions import InvalidJobName, InvalidMaxAttempts, InvalidSource

JOB_NAME_MIN_LENGTH = 3
JOB_NAME_MAX_LENGTH = 120
SOURCE_URI_MAX_LENGTH = 2048
MAX_ATTEMPTS_LIMIT = 10


class SourceType(StrEnum):
    WEB = "web"  # crawl a public website
    API = "api"  # pull from a partner/vendor API
    FILE = "file"  # import a file drop (object storage or SFTP)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = frozenset({JobStatus.QUEUED, JobStatus.RUNNING})
TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.CANCELLED})

# Which URI schemes each source type may use. API sources must be encrypted in transit.
_ALLOWED_SCHEMES: dict[SourceType, frozenset[str]] = {
    SourceType.WEB: frozenset({"http", "https"}),
    SourceType.API: frozenset({"https"}),
    SourceType.FILE: frozenset({"s3", "sftp"}),
}


@dataclass(frozen=True, slots=True)
class JobName:
    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if not JOB_NAME_MIN_LENGTH <= len(normalized) <= JOB_NAME_MAX_LENGTH:
            raise InvalidJobName(f"Job name must contain {JOB_NAME_MIN_LENGTH}-{JOB_NAME_MAX_LENGTH} characters")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class DataSource:
    """Where the data comes from. Type and URI are validated together."""

    type: SourceType
    uri: str

    def __post_init__(self) -> None:
        uri = self.uri.strip()
        if not uri or len(uri) > SOURCE_URI_MAX_LENGTH:
            raise InvalidSource(f"Source URI must contain 1-{SOURCE_URI_MAX_LENGTH} characters")
        parsed = urlparse(uri)
        allowed = _ALLOWED_SCHEMES[self.type]
        if parsed.scheme.lower() not in allowed:
            raise InvalidSource(f"A {self.type.value} source must use one of: {', '.join(sorted(allowed))}")
        if not parsed.netloc:
            raise InvalidSource("Source URI must include a host or bucket")
        if parsed.username or parsed.password:
            raise InvalidSource("Source URI must not embed credentials; use a credentials reference instead")
        object.__setattr__(self, "uri", uri)


@dataclass(frozen=True, slots=True)
class MaxAttempts:
    value: int

    def __post_init__(self) -> None:
        if not 1 <= self.value <= MAX_ATTEMPTS_LIMIT:
            raise InvalidMaxAttempts(f"Max attempts must be between 1 and {MAX_ATTEMPTS_LIMIT}")
