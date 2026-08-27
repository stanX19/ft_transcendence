"""Administrator-only user and role transport schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.features.users.models import UserRole


class AdminUserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    bio: str
    role: str
    is_online: bool
    created_at: datetime


class AdminUserEnvelope(BaseModel):
    user: AdminUserResponse


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    page: int
    page_size: int
    total: int


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    bio: str | None = Field(default=None, max_length=2000)
    email: str | None = Field(default=None, min_length=3, max_length=320)

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name", "bio", "email", mode="before")
    @classmethod
    def trim_values(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class AdminRoleUpdate(BaseModel):
    role: UserRole

    model_config = ConfigDict(extra="forbid")
