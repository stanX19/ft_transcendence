"""Pydantic contracts for catalog reads, writes, and search."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _trim(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _optional_text(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class BookCreate(BaseModel):
    """Client-supplied fields for creating a book.

    ``available_copies`` may be sent by a complete-record client, but the
    server initializes it from ``total_copies`` and owns the value.
    """

    isbn: str | None = Field(default=None, max_length=32)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10000)
    category: str = Field(min_length=1, max_length=120)
    publication_year: int | None = Field(default=None, ge=0, le=3000)
    total_copies: int = Field(ge=0)
    available_copies: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    _trim_text = field_validator(
        "slug",
        "title",
        "author",
        "description",
        "category",
        mode="before",
    )(_trim)
    _normalize_isbn = field_validator("isbn", mode="before")(_optional_text)


class BookUpdate(BaseModel):
    """Allowed partial catalog edits.

    ``available_copies`` is accepted for compatibility with clients that send
    a complete record, but the service deliberately ignores it.
    """

    isbn: str | None = Field(default=None, max_length=32)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    publication_year: int | None = Field(default=None, ge=0, le=3000)
    total_copies: int | None = Field(default=None, ge=0)
    available_copies: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    _trim_text = field_validator(
        "slug",
        "title",
        "author",
        "description",
        "category",
        mode="before",
    )(_trim)
    _normalize_isbn = field_validator("isbn", mode="before")(_optional_text)

    @model_validator(mode="after")
    def require_an_edit(self) -> "BookUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one book field is required.")
        return self


class BookResponse(BaseModel):
    """Public catalog representation."""

    id: int
    isbn: str | None
    slug: str
    title: str
    author: str
    description: str
    category: str
    publication_year: int | None
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookEnvelope(BaseModel):
    book: BookResponse


class BookListResponse(BaseModel):
    items: list[BookResponse]
    page: int
    page_size: int
    total: int


SortOption = Literal["title", "author", "newest"]
