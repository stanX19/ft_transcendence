"""Deterministic local catalog seed contracts."""

from __future__ import annotations

from sqlalchemy import func, select


def test_seed_is_local_reproducible_and_populates_at_least_500_useful_books(db_session) -> None:
    from app.features.books.models import Book
    from app.seed import seed

    seed()
    first_count = db_session.scalar(select(func.count()).select_from(Book)) or 0
    assert first_count >= 500
    sample = db_session.scalars(select(Book).order_by(Book.id).limit(5)).all()
    assert sample
    assert all(book.title and book.author and book.description and book.category for book in sample)
    assert len({book.category for book in sample}) >= 2

    seed()
    second_count = db_session.scalar(select(func.count()).select_from(Book)) or 0
    assert second_count == first_count
