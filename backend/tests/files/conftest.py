"""Shared fixtures for secure file asset tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image


def png_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), (40, 120, 200))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def jpeg_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), (200, 120, 40))
    output = BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture
def create_file_book(db_session) -> Callable[..., object]:
    def make_book(*, title: str | None = None) -> object:
        from app.features.books.models import Book

        token = uuid4().hex
        now = datetime.now(timezone.utc)
        book = Book(
            isbn=f"978{token[:10]}",
            slug=f"file-{token}",
            title=title or f"File Fixture Book {token}",
            author="File Fixture Author",
            description="A book used by secure file tests.",
            category="File Testing",
            publication_year=2024,
            total_copies=2,
            available_copies=2,
            created_at=now,
            updated_at=now,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return make_book


@pytest.fixture
def privileged_file_client(client_factory, register_user, db_session):
    def make_client(role: str = "LIBRARIAN"):
        from sqlalchemy import select

        from app.features.users.models import User

        client = client_factory()
        registration = register_user(client, display_name=f"{role.title()} File Manager")
        assert registration.status_code == 201, registration.text
        user_id = registration.json()["user"]["id"]
        user = db_session.scalar(select(User).where(User.id == user_id))
        assert user is not None
        user.role = role
        db_session.commit()
        return client

    return make_client
