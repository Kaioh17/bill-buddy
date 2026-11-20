"""Request and response schemas for signup and login."""

import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schema.general import ORMModel

# Limits keep oversized payloads out of the hasher and the database.
NAME_MAX = 50
EMAIL_MAX = 254  # RFC 5321 maximum for an address
# 12+ follows current NIST/OWASP guidance for strong passwords. The cap only bounds
# hashing cost, argon2 has no 72 byte limit like bcrypt.
PASSWORD_MIN = 12
PASSWORD_MAX = 128

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX)
]
Password = Annotated[str, Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys are an error, not ignored


class _EmailMixin(_Request):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _clean_email(cls, v):
        # Length is checked first so a huge string never reaches the email parser.
        if isinstance(v, str):
            if len(v) > EMAIL_MAX:
                raise ValueError(f"Email must be at most {EMAIL_MAX} characters")
            return v.strip().lower()
        return v


class SignupRequest(_EmailMixin):
    first_name: Name
    last_name: Name
    password: Password
    confirm_password: str = Field(max_length=PASSWORD_MAX)

    @model_validator(mode="after")
    def _passwords_match(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(_EmailMixin):
    # No minimum here: login must not reveal or depend on the current password policy.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class UserOut(ORMModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    created_at: datetime


class Token(BaseModel):
    """OAuth2 token response shape."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
