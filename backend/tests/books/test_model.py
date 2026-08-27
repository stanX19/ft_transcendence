"""Database contracts for the catalog model and migration."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


EXPECTED_COLUMNS = {
    "id",
    "isbn",
    "slug",
    "title",
    "author",
    "description",
    "category",
    "publication_year",
    "total_copies",
    "available_copies",
    "created_at",
    "updated_at",
}


def test_books_model_is_registered_before_alembic_imports_metadata() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["APP_ENV"] = "test"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.model_registry import Base; assert 'books' in Base.metadata.tables",
        ],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_books_table_has_catalog_fields_without_file_asset_foreign_keys() -> None:
    from app.core.database import Base, engine
    from app.features.books.models import Book

    assert Book.__table__ is Base.metadata.tables["books"]
    columns = inspect(engine).get_columns("books")
    assert {column["name"] for column in columns} >= EXPECTED_COLUMNS
    assert not {"cover_file_id", "document_file_id"}.intersection(Book.__table__.c.keys())


@pytest.mark.parametrize(
    "values",
    [
        {"total_copies": -1, "available_copies": 0},
        {"total_copies": 1, "available_copies": -1},
        {"total_copies": 1, "available_copies": 2},
    ],
)
def test_database_rejects_invalid_inventory_counts(db_session, values) -> None:
    from app.features.books.models import Book

    db_session.add(
        Book(
            title="Invalid inventory",
            author="QA",
            description="Invalid inventory fixture",
            category="Testing",
            **values,
        )
    )
    with pytest.raises(SQLAlchemyError):
        db_session.commit()


def test_isbn_is_unique_when_present_but_optional(db_session) -> None:
    from app.features.books.models import Book

    isbn = f"978{uuid4().hex[:10]}"
    first = Book(
        isbn=isbn,
        title="ISBN One",
        author="QA",
        description="First ISBN fixture",
        category="Testing",
        total_copies=1,
        available_copies=1,
    )
    without_isbn = Book(
        isbn=None,
        title="No ISBN",
        author="QA",
        description="Nullable ISBN fixture",
        category="Testing",
        total_copies=1,
        available_copies=1,
    )
    db_session.add_all([first, without_isbn])
    db_session.commit()

    duplicate = Book(
        isbn=isbn,
        title="ISBN Duplicate",
        author="QA",
        description="Duplicate ISBN fixture",
        category="Testing",
        total_copies=1,
        available_copies=1,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
