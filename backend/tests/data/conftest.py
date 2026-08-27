"""Fixtures and wire-format helpers for catalog import/export contracts."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import xml.etree.ElementTree as ET

import pytest
from sqlalchemy import select


EXPORT_ENDPOINT = "/api/admin/import-export/export"
IMPORT_ENDPOINT = "/api/admin/import-export/import"

IMPORT_FIELDS = (
    "isbn",
    "slug",
    "title",
    "author",
    "description",
    "category",
    "publication_year",
    "total_copies",
)

FORMAT_DETAILS = {
    "csv": ("text/csv", "catalog.csv"),
    "json": ("application/json", "catalog.json"),
    "xml": ("application/xml", "catalog.xml"),
}


@pytest.fixture
def data_marker() -> str:
    """Use a fresh marker because the shared PostgreSQL DB persists between runs."""

    return f"data-{uuid4().hex}"


@pytest.fixture
def role_client(
    client_factory,
    register_user,
    login_user,
    unique_email,
    db_session,
) -> Callable[..., object]:
    """Register, promote, and authenticate a user for a requested role."""

    def make_client(role: str = "MEMBER") -> object:
        from app.features.users.models import User, UserRole

        email = unique_email(f"data-{role.lower()}")
        setup_client = client_factory()
        registration = register_user(
            setup_client,
            email=email,
            display_name=f"Data {role.title()} {uuid4().hex[:8]}",
        )
        assert registration.status_code == 201, registration.text

        user = db_session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole(role)
        db_session.commit()

        authenticated_client = client_factory()
        login = login_user(authenticated_client, email=email)
        assert login.status_code == 200, login.text
        return authenticated_client

    return make_client


@pytest.fixture
def create_data_book(db_session) -> Callable[..., object]:
    """Persist a unique real catalog row for export and update assertions."""

    def make_book(
        *,
        marker: str | None = None,
        isbn: str | None = None,
        title: str | None = None,
        total_copies: int = 4,
        available_copies: int | None = None,
    ) -> object:
        from app.features.books.models import Book

        token = marker or uuid4().hex
        timestamp = datetime.now(timezone.utc)
        book = Book(
            isbn=isbn or f"978{uuid4().hex[:10]}",
            slug=f"data-{token}",
            title=title or f"Data Export Book {token}",
            author=f"Data Author {token}",
            description=f"Data import/export description {token}.",
            category="Data QA",
            publication_year=2026,
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


def book_record(
    marker: str,
    *,
    isbn: str | None = None,
    title: str | None = None,
    total_copies: int = 3,
) -> dict[str, Any]:
    """Return the editable catalog fields accepted by a bulk import."""

    return {
        "isbn": isbn or f"978{uuid4().hex[:10]}",
        "slug": f"import-{marker}",
        "title": title or f"Imported Data Book {marker}",
        "author": f"Imported Author {marker}",
        "description": f"Imported description {marker}.",
        "category": "Imported QA",
        "publication_year": 2026,
        "total_copies": total_copies,
    }


def encode_records(records: list[dict[str, Any]], file_format: str) -> bytes:
    """Encode records in the three formats required by the data module."""

    if file_format == "json":
        return json.dumps(records).encode("utf-8")

    if file_format == "csv":
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=IMPORT_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)
        return buffer.getvalue().encode("utf-8")

    if file_format == "xml":
        root = ET.Element("catalog")
        for record in records:
            book = ET.SubElement(root, "book")
            for field in IMPORT_FIELDS:
                element = ET.SubElement(book, field)
                value = record.get(field)
                element.text = "" if value is None else str(value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    raise AssertionError(f"Unsupported test format: {file_format}")


def upload_records(client, records: list[dict[str, Any]], file_format: str):
    content_type, filename = FORMAT_DETAILS[file_format]
    return client.post(
        IMPORT_ENDPOINT,
        files={
            "file": (
                filename,
                encode_records(records, file_format),
                content_type,
            )
        },
    )


def summary_from(response_json: dict[str, Any]) -> dict[str, Any]:
    """Normalize the documented summary envelope while keeping counts strict."""

    summary = response_json.get("summary", response_json)
    assert isinstance(summary, dict)
    for field in ("inserted", "updated", "rejected"):
        assert isinstance(summary.get(field), int), response_json
    return summary


def validation_errors_from(response_json: dict[str, Any]) -> list[Any]:
    """Find row-level errors in either the result or validation-error envelope."""

    errors = response_json.get("errors")
    if errors is None:
        errors = response_json.get("validation_errors")
    if errors is None and isinstance(response_json.get("error"), dict):
        errors = response_json["error"].get("details")
    assert isinstance(errors, list), response_json
    return errors


def book_by_isbn(db_session, isbn: str):
    from app.features.books.models import Book

    db_session.expire_all()
    return db_session.scalar(select(Book).where(Book.isbn == isbn))
