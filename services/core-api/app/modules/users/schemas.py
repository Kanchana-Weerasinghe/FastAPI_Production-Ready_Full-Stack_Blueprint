from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from pydantic.alias_generators import to_camel


def _user_fields(user: Any) -> dict[str, Any]:
    """Maps the ORM user to public fields, exposing booleans instead of raw timestamps/secrets."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "email_verified": user.email_verified_at is not None,
        "mfa_enabled": user.mfa_enabled_at is not None,
    }


class User(BaseModel):
    """Public user profile schema."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., description="User's unique username")
    role: str = Field("user", description="Authorization role")
    email_verified: bool = Field(False, description="Whether the email address has been verified")
    mfa_enabled: bool = Field(False, description="Whether TOTP multi-factor authentication is enabled")

    @model_validator(mode="before")
    @classmethod
    def _from_model(cls, data: Any) -> Any:
        return _user_fields(data) if hasattr(data, "email_verified_at") else data


class UserAdminView(User):
    """User fields visible to administrators."""

    created_at: datetime | None = Field(None, description="Account creation time")
    locked_until: datetime | None = Field(None, description="Login lockout expiry, if locked")

    @model_validator(mode="before")
    @classmethod
    def _admin_from_model(cls, data: Any) -> Any:
        if hasattr(data, "email_verified_at"):
            return {**_user_fields(data), "created_at": data.created_at, "locked_until": data.locked_until}
        return data


class FindUser(BaseModel):
    """Schema for filtering users in query results."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    email__eq: EmailStr | None = Field(None, alias="email", description="Filter by exact email match")
