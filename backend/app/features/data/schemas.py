"""Transport schemas for catalog data exchange."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CatalogFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"


class ImportIssue(BaseModel):
    record: int | None = Field(default=None, ge=1)
    message: str
    fields: list[str] = Field(default_factory=list)


class ImportCounts(BaseModel):
    inserted: int = Field(ge=0)
    updated: int = Field(ge=0)
    rejected: int = Field(ge=0)


class ImportResult(BaseModel):
    format: CatalogFormat
    inserted: int = Field(ge=0)
    updated: int = Field(ge=0)
    rejected: int = Field(ge=0)
    errors: list[ImportIssue] = Field(default_factory=list)
    summary: ImportCounts
