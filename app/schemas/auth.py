import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


_PASSWORD_COMPLEXITY_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$")
_HTML_TAG_RE = re.compile(r"<[^>]*>")


def _validate_password_complexity(value: str) -> str:
    if not _PASSWORD_COMPLEXITY_RE.match(value):
        raise ValueError("Password must contain at least one uppercase letter, one lowercase letter, and one digit")
    return value


def _normalize_email(value: EmailStr) -> str:
    return str(value).lower().strip()


def _sanitize_name(value: str) -> str:
    return _HTML_TAG_RE.sub("", value).strip()


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    _normalize_email = field_validator("email", mode="before")(_normalize_email)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return _sanitize_name(v)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    _normalize_email = field_validator("email", mode="before")(_normalize_email)


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    current_password: str = Field(min_length=8, max_length=128)

    _normalize_email = field_validator("email", mode="before")(_normalize_email)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return _sanitize_name(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class DeleteAccountRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    email_verified_at: datetime | None
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in_minutes: int
    email_verified_at: datetime | None = None


class MessageResponse(BaseModel):
    message: str
