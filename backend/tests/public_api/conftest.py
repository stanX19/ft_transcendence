"""Fixtures for the API-key protected catalog integration surface."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def public_api_key() -> str:
    from app.core.config import get_settings

    return get_settings().public_api_key


@pytest.fixture
def public_headers(public_api_key: str) -> dict[str, str]:
    return {"X-API-Key": public_api_key}


@pytest.fixture
def create_book(db_session) -> Callable[..., object]:
    """Persist a unique catalog row for each public API contract."""

    def make_book(
        *,
        title: str | None = None,
        author: str = "QA Public API Author",
        description: str = "A public API catalog description.",
        category: str = "Public API",
        isbn: str | None = None,
        publication_year: int | None = 2024,
        total_copies: int = 3,
        available_copies: int | None = None,
    ) -> object:
        from app.features.books.models import Book

        token = uuid4().hex
        timestamp = datetime.now(timezone.utc)
        book = Book(
            isbn=isbn if isbn is not None else f"978{token[:10]}",
            slug=f"public-api-{token}",
            title=title or f"Public API Book {token}",
            author=author,
            description=description,
            category=category,
            publication_year=publication_year,
            total_copies=total_copies,
            available_copies=(
                total_copies if available_copies is None else available_copies
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return make_book
