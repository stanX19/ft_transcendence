"""SQLAlchemy models for the library catalog."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Book(Base):
    """A catalog record and its current physical-copy inventory."""

    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("isbn", name="uq_books_isbn"),
        CheckConstraint(
            "total_copies >= 0",
            name="ck_books_total_copies_nonnegative",
        ),
        CheckConstraint(
            "available_copies >= 0",
            name="ck_books_available_copies_nonnegative",
        ),
        CheckConstraint(
            "available_copies <= total_copies",
            name="ck_books_available_copies_lte_total",
        ),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
        Index("ix_books_category", "category"),
        Index(
            "ix_books_search_document",
            "search_document",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Slugs are API-friendly but not an identity constraint. The default also
    # keeps direct SQLAlchemy fixtures valid while the API derives a real slug.
    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    publication_year: Mapped[int | None] = mapped_column(nullable=True)
    total_copies: Mapped[int] = mapped_column(nullable=False, default=0)
    available_copies: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    search_document: Mapped[object] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', "
            "coalesce(title, '') || ' ' || "
            "coalesce(author, '') || ' ' || "
            "coalesce(description, '') || ' ' || "
            "coalesce(category, '')",
            persisted=True,
        ),
        nullable=True,
    )
