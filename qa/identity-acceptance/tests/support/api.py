"""A thin HTTP client that behaves like the web app: cookie session plus the CSRF header on writes."""

import uuid
from dataclasses import dataclass

import httpx

from tests.support.settings import Settings

TEST_PASSWORD = "SecurePass123!"


@dataclass(frozen=True, slots=True)
class Credentials:
    email: str
    password: str

    def as_json(self) -> dict[str, str]:
        return {"email": self.email, "password": self.password}


class ApiSession:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.Client(base_url=settings.base_url, timeout=15.0)

    def sign_in(self, credentials: Credentials) -> httpx.Response:
        response = self.http.post("/v1/auth/signin", json=credentials.as_json())
        # Python's cookie jar rejects `Domain=localhost` (browsers accept it), so keep the cookies host-agnostic.
        received = dict(
            header.split(";", 1)[0].strip().split("=", 1) for header in response.headers.get_list("set-cookie")
        )
        if received:
            self.http.cookies.clear()
            for name, value in received.items():
                self.http.cookies.set(name, value)
        csrf = received.get(self.settings.csrf_cookie)
        if csrf:
            self.http.headers[self.settings.csrf_header] = csrf
        return response

    def close(self) -> None:
        self.http.close()


def unique_credentials() -> Credentials:
    return Credentials(email=f"qa_{uuid.uuid4().hex[:12]}@example.com", password=TEST_PASSWORD)
