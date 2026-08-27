"""Small database helpers shared by catalog contract tests."""

from __future__ import annotations

from uuid import uuid4


def add_book(db_session, **overrides):
    """Insert a distinct book directly for focused API tests."""

    from app.features.books.models import Book

    marker = uuid4().hex
    values = {
        "isbn": f"978{marker[:10]}",
        "title": f"QA Book {marker}",
        "author": "QA Author",
        "description": "A practical story about catalog testing.",
        "category": "Testing",
        "publication_year": 2025,
        "total_copies": 3,
        "available_copies": 3,
    }
    values.update(overrides)
    book = Book(**values)
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book
