"""Shared fixtures for local RAG contract tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest


@pytest.fixture
def create_ai_book(db_session) -> Callable[..., Any]:
    """Persist a uniquely identifiable catalog record for RAG tests."""

    def make_book(
        *,
        title: str | None = None,
        author: str = "RAG QA Author",
        description: str = "A local catalog description for RAG QA.",
        category: str = "RAG QA",
        total_copies: int = 2,
    ) -> Any:
        from app.features.books.models import Book

        token = uuid4().hex
        timestamp = datetime.now(timezone.utc)
        book = Book(
            isbn=f"978{token[:10]}",
            slug=f"rag-{token}",
            title=title or f"RAG QA Book {token}",
            author=author,
            description=description,
            category=category,
            publication_year=2026,
            total_copies=total_copies,
            available_copies=total_copies,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return make_book
