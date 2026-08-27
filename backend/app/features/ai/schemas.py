"""Small, provider-neutral contracts for catalog-grounded answers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceBook(BaseModel):
    """Catalog metadata that can be displayed beside an assistant answer."""

    book_id: int = Field(gt=0)
    title: str
    author: str
    category: str
    isbn: str | None = None

    model_config = ConfigDict(extra="forbid")


class RAGAnswer(BaseModel):
    """A generated answer and the records that grounded its context."""

    answer: str
    sources: list[SourceBook]

    model_config = ConfigDict(extra="forbid")
