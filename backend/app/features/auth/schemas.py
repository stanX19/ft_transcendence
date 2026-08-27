"""Request schemas for account registration and login."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    """Normalized credentials accepted by auth endpoints."""

    # Keep validation structural rather than checking DNS or reserved test
    # domains. The application does not send verification mail, and allowing
    # addresses such as ``reader@example.test`` keeps automated and local
    # environments deterministic while still rejecting malformed input.
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

    model_config = ConfigDict(extra="ignore")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not _EMAIL_PATTERN.fullmatch(normalized):
                raise ValueError("Enter a valid email address.")
            return normalized
        return value


class RegisterRequest(Credentials):
    """Registration payload; role is intentionally not client-controlled."""

    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
