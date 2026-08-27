"""Catalog queries and business rules."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.features.books.models import Book
from app.features.books.schemas import BookCreate, BookUpdate, SortOption


class BookInventoryConflict(Exception):
    """Raised when an edit would discard already-borrowed copies."""


class BookHasActiveLoan(Exception):
    """Raised when deleting a book that still has borrowed inventory."""


def _escape_like(value: str) -> str:
    """Escape wildcard characters so bounded user input stays a literal search."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _contains(column, value: str):
    return column.ilike(f"%{_escape_like(value)}%", escape="\\")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug[:200] or "book"


def get_book(db: Session, book_id: int) -> Book | None:
    return db.scalar(select(Book).where(Book.id == book_id))


def list_books(
    db: Session,
    *,
    q: str | None,
    author: str | None,
    category: str | None,
    available: bool | None,
    sort: SortOption,
    page: int,
    page_size: int,
) -> tuple[list[Book], int]:
    """Run a bounded, parameterized catalog query and return rows plus count."""

    statement = select(Book)

    terms = [term for term in (q or "").split() if term]
    for term in terms:
        statement = statement.where(
            or_(
                _contains(Book.title, term),
                _contains(Book.author, term),
                _contains(Book.description, term),
                _contains(Book.isbn, term),
            )
        )

    if author:
        statement = statement.where(_contains(Book.author, author.strip()))
    if category:
        statement = statement.where(_contains(Book.category, category.strip()))
    if available is True:
        statement = statement.where(Book.available_copies > 0)
    elif available is False:
        statement = statement.where(Book.available_copies == 0)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0

    if sort == "author":
        ordering = (func.lower(Book.author), func.lower(Book.title), Book.id)
    elif sort == "newest":
        ordering = (Book.created_at.desc(), Book.id.desc())
    else:
        ordering = (func.lower(Book.title), Book.id)

    rows = list(
        db.scalars(
            statement.order_by(*ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def create_book(db: Session, payload: BookCreate) -> Book:
    values = payload.model_dump()
    title = values["title"]
    supplied_slug = values.pop("slug")
    values.pop("available_copies", None)
    values["slug"] = _slugify(supplied_slug or title)
    values["available_copies"] = values["total_copies"]
    book = Book(**values)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, book: Book, payload: BookUpdate) -> Book:
    values = payload.model_dump(exclude_unset=True)
    # Inventory is derived from the number of borrowed copies and cannot be
    # directly edited by a client, even when sent as part of a full record.
    values.pop("available_copies", None)

    if "total_copies" in values:
        new_total = values["total_copies"]
        borrowed_copies = book.total_copies - book.available_copies
        if new_total < borrowed_copies:
            raise BookInventoryConflict
        book.total_copies = new_total
        book.available_copies = new_total - borrowed_copies
        values.pop("total_copies")

    for field in (
        "isbn",
        "slug",
        "title",
        "author",
        "description",
        "category",
        "publication_year",
    ):
        if field in values:
            value = values[field]
            if field == "slug":
                value = _slugify(value or book.title)
            setattr(book, field, value)

    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book: Book) -> None:
    """Delete a safe book.

    Once the Loan model exists, replace this conservative borrowed-inventory
    check with a query for ``Loan.returned_at.is_(None)`` by ``book_id``. Until
    then, a non-zero borrowed count must block deletion so inventory cannot be
    orphaned by a catalog edit.
    """

    if book.available_copies < book.total_copies:
        raise BookHasActiveLoan
    db.delete(book)
    db.commit()
