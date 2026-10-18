"""Application request/result types independent of HTTP and Pydantic schemas."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class SessionTokens:
    access_token: str
    refresh_token: str
    csrf_token: str


@dataclass(frozen=True, slots=True)
class SignInOutcome:
    mfa_required: bool = False
    mfa_token: str | None = None


@dataclass(frozen=True, slots=True)
class MfaSetupDetails:
    secret: str
    otpauth_uri: str
