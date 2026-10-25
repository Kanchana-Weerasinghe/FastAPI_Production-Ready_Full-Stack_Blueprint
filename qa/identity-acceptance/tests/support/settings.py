"""Where and how to reach the system under test. Everything comes from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True, slots=True)
class Settings:
    base_url: str
    admin_email: str
    admin_password: str
    openapi_path: Path
    spec_path: Path
    login_max_failed_attempts: int
    csrf_cookie: str
    csrf_header: str
    access_cookie: str


def load_settings() -> Settings:
    return Settings(
        base_url=os.environ.get("QA_BASE_URL", "http://localhost:8000").rstrip("/"),
        admin_email=os.environ.get("QA_ADMIN_EMAIL", "admin@example.com"),
        admin_password=os.environ.get("QA_ADMIN_PASSWORD", "Password123!"),
        openapi_path=Path(os.environ.get("QA_OPENAPI", REPO_ROOT / "services" / "identity" / "openapi.json")),
        spec_path=Path(os.environ.get("QA_SPEC", REPO_ROOT / "specs" / "identity" / "users.rules.yaml")),
        login_max_failed_attempts=int(os.environ.get("QA_LOGIN_MAX_FAILED_ATTEMPTS", "5")),
        csrf_cookie=os.environ.get("QA_CSRF_COOKIE", "csrf_token"),
        csrf_header=os.environ.get("QA_CSRF_HEADER", "X-CSRF-Token"),
        access_cookie=os.environ.get("QA_ACCESS_COOKIE", "x-path-token"),
    )
