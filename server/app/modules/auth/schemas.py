from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

PASSWORD_MIN_LENGTH = 8
BCRYPT_MAX_BYTES = 72


def _within_bcrypt_limit(value: str) -> str:
    """bcrypt only uses the first 72 bytes (and bcrypt>=5 rejects longer input), so cap by encoded size."""
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes")
    return value


LoginPassword = Annotated[str, Field(min_length=1), AfterValidator(_within_bcrypt_limit)]
NewPassword = Annotated[
    str,
    Field(
        min_length=PASSWORD_MIN_LENGTH,
        description=f"{PASSWORD_MIN_LENGTH} characters to {BCRYPT_MAX_BYTES} bytes",
    ),
    AfterValidator(_within_bcrypt_limit),
]
TotpCode = Annotated[str, Field(pattern=r"^\d{6}$", description="6-digit code from the authenticator app")]

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SignIn(BaseModel):
    """Schema for user login requests."""

    email: EmailStr = Field(..., description="User's registered email address")
    password: LoginPassword = Field(..., description="User's password")


class SignUp(BaseModel):
    """Schema for new user registration requests."""

    email: EmailStr = Field(..., description="Unique email address for the new account")
    password: NewPassword


class SignInResponse(BaseModel):
    """Sign-in result. When `mfa_required` is true no session was created; call /v1/auth/mfa/verify."""

    model_config = _camel
    mfa_required: bool = False
    mfa_token: str | None = Field(default=None, description="Short-lived challenge token for /v1/auth/mfa/verify")


class MfaVerify(BaseModel):
    model_config = _camel
    mfa_token: str
    code: TotpCode


class MfaSetupResponse(BaseModel):
    model_config = _camel
    secret: str = Field(..., description="Base32 TOTP secret (for manual entry)")
    otpauth_uri: str = Field(..., description="otpauth:// URI to render as a QR code")


class MfaCode(BaseModel):
    code: TotpCode


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)


class PasswordReset(BaseModel):
    model_config = _camel
    token: str = Field(..., min_length=16, max_length=256)
    new_password: NewPassword


class PasswordChange(BaseModel):
    model_config = _camel
    current_password: LoginPassword
    new_password: NewPassword
