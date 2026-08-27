"""Shared fixtures for catalog API contract tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def role_client(
    client_factory,
    register_user,
    login_user,
    unique_email,
    db_session,
) -> Callable[..., object]:
    """Create a registered user, grant a test role, and return a logged-in client."""

    def make_client(
        role: str = "MEMBER",
        *,
        display_name: str | None = None,
    ) -> object:
        from sqlalchemy import select

        from app.features.users.models import User

        email = unique_email(f"books-{role.lower()}")
        setup_client = client_factory()
        registration = register_user(
            setup_client,
            email=email,
            display_name=display_name or f"{role.title()} Catalog User",
        )
        assert registration.status_code == 201, registration.text

        user = db_session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db_session.commit()

        authenticated_client = client_factory()
        login = login_user(authenticated_client, email=email)
        assert login.status_code == 200, login.text
        return authenticated_client

    return make_client


@pytest.fixture
def create_book(db_session) -> Callable[..., object]:
    """Persist a unique catalog row for API tests that need real DB state."""

    def make_book(
        *,
        title: str | None = None,
        author: str = "QA Catalog Author",
        description: str = "A useful catalog description for QA.",
        category: str = "QA",
        isbn: str | None = None,
        publication_year: int | None = 2024,
        total_copies: int = 3,
        available_copies: int | None = None,
        created_at: datetime | None = None,
    ) -> object:
        from app.features.books.models import Book

        token = uuid4().hex
        book = Book(
            isbn=isbn if isbn is not None else f"978{token[:10]}",
            slug=f"qa-{token}",
            title=title or f"QA Catalog Book {token}",
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
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=created_at or datetime.now(timezone.utc),
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return make_book
