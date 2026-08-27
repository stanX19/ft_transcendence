"""Shared fixtures for loan and inventory lifecycle contracts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def create_loan_user(db_session) -> Callable[..., object]:
    """Create a direct database user for service and model tests."""

    def make_user(*, display_name: str = "Loan Test User") -> object:
        from app.features.users.models import User, UserRole

        token = uuid4().hex
        user = User(
            email=f"loan-{token}@example.test",
            password_hash="test-only-hash",
            display_name=display_name,
            bio="",
            role=UserRole.MEMBER,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return make_user


@pytest.fixture
def create_loan_book(db_session) -> Callable[..., object]:
    """Create a direct book with caller-controlled inventory."""

    def make_book(
        *,
        title: str | None = None,
        total_copies: int = 2,
        available_copies: int | None = None,
    ) -> object:
        from app.features.books.models import Book

        token = uuid4().hex
        timestamp = datetime.now(timezone.utc)
        book = Book(
            isbn=f"978{token[:10]}",
            slug=f"loan-{token}",
            title=title or f"Loan Test Book {token}",
            author="Loan Test Author",
            description="A book used by loan lifecycle tests.",
            category="Loan Testing",
            publication_year=2024,
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
