"""SQLAlchemy model for borrowing and returning catalog books."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Return an aware UTC timestamp for loan lifecycle defaults."""

    return datetime.now(timezone.utc)


class Loan(Base):
    """A user's borrow of one physical catalog copy."""

    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("due_at >= borrowed_at", name="ck_loans_due_after_borrowed"),
        Index(
            "uq_loans_active_user_book",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
        Index("ix_loans_user_id", "user_id"),
        Index("ix_loans_book_id", "book_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id"),
        nullable=False,
    )
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
