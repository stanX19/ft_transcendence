"""Pydantic request and response shapes for user-facing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPrivateResponse(BaseModel):
    """Account fields safe for the authenticated account owner."""

    id: int
    email: str
    display_name: str
    bio: str
    role: str
    is_online: bool

    model_config = ConfigDict(from_attributes=True)


class UserPublicResponse(BaseModel):
    """The intentionally small public profile contract."""

    id: int
    display_name: str
    bio: str
    is_online: bool


class UserDirectoryResponse(BaseModel):
    """A paginated list of public profile stubs."""

    items: list[UserPublicResponse]
    page: int
    page_size: int
    total: int


class UserProfileUpdate(BaseModel):
    """Fields an authenticated user may change on their own profile."""

    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    bio: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name", "bio", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


def normalize_display_name(value: str) -> str:
    """Trim a display name before applying the schema constraints."""

    return value.strip()
