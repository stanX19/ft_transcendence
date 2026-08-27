"""Shared fixtures for catalog search contract tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def create_search_book(db_session) -> Callable[..., object]:
    """Persist a catalog row with caller-controlled search fields."""

    def make_book(
        *,
        title: str | None = None,
        author: str = "Search QA Author",
        description: str = "Search QA description.",
        category: str = "Search QA",
        isbn: str | None = None,
        publication_year: int | None = 2024,
        total_copies: int = 2,
        available_copies: int | None = None,
        created_at: datetime | None = None,
    ) -> object:
        from app.features.books.models import Book

        token = uuid4().hex
        timestamp = created_at or datetime.now(timezone.utc)
        book = Book(
            isbn=isbn or f"978{token[:10]}",
            slug=f"search-{token}",
            title=title or f"Search QA Book {token}",
            author=author,
            description=description,
            category=category,
            publication_year=publication_year,
            total_copies=total_copies,
            available_copies=(
                total_copies
                if available_copies is None
                else available_copies
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return make_book
