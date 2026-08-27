"""Transactional loan operations and current-user loan queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypeAlias

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.books.models import Book
from app.features.loans.models import Loan
from app.features.users.models import UserRole


class LoanNotFound(Exception):
    """Raised when a requested loan does not exist."""


class BookNotFound(Exception):
    """Raised when a requested book does not exist."""


class BookUnavailable(Exception):
    """Raised when no physical copy can be borrowed."""


class LoanAlreadyActive(Exception):
    """Raised when a user already holds the requested book."""


class LoanForbidden(Exception):
    """Raised when the actor cannot return the selected loan."""


RoleLike: TypeAlias = str | UserRole


def _role_value(role: RoleLike) -> str:
    return role.value if isinstance(role, UserRole) else str(role).upper()


def _is_privileged(role: RoleLike) -> bool:
    return _role_value(role) in {UserRole.LIBRARIAN.value, UserRole.ADMIN.value}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def borrow_book(
    db: Session,
    *,
    user_id: int,
    book_id: int,
    borrowed_at: datetime | None = None,
) -> Loan:
    """Borrow one copy while serializing all borrowers of the same book.

    Locking the book before inspecting or inserting a loan means concurrent
    borrowers cannot both observe the final available copy.
    """

    book = db.scalar(
        select(Book).where(Book.id == book_id).with_for_update()
    )
    if book is None:
        raise BookNotFound

    active_loan = db.scalar(
        select(Loan)
        .where(
            Loan.user_id == user_id,
            Loan.book_id == book_id,
            Loan.returned_at.is_(None),
        )
        .with_for_update()
    )
    if active_loan is not None:
        raise LoanAlreadyActive
    if book.available_copies <= 0:
        raise BookUnavailable

    borrowed = _as_utc(borrowed_at or datetime.now(timezone.utc))
    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        borrowed_at=borrowed,
        due_at=borrowed + timedelta(days=get_settings().loan_days),
    )
    book.available_copies -= 1
    db.add(loan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise LoanAlreadyActive from None
    db.refresh(loan)
    return loan


def return_loan(
    db: Session,
    loan_id: int,
    *,
    actor_user_id: int,
    actor_role: RoleLike,
    returned_at: datetime | None = None,
) -> Loan:
    """Return a loan once; repeated owner returns are successful no-ops."""

    # Read the book id without locking, then acquire locks in the same
    # book-before-loan order used by borrow_book to avoid lock inversions.
    initial_loan = db.scalar(select(Loan).where(Loan.id == loan_id))
    if initial_loan is None:
        raise LoanNotFound
    book = db.scalar(
        select(Book).where(Book.id == initial_loan.book_id).with_for_update()
    )
    locked_loan = db.scalar(
        select(Loan)
        .where(Loan.id == loan_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if locked_loan is None or book is None:
        raise LoanNotFound
    if locked_loan.user_id != actor_user_id and not _is_privileged(actor_role):
        raise LoanForbidden

    if locked_loan.returned_at is None:
        locked_loan.returned_at = _as_utc(returned_at or datetime.now(timezone.utc))
        book.available_copies += 1
    db.commit()
    db.refresh(locked_loan)
    return locked_loan


def list_user_loans(
    db: Session,
    *,
    user_id: int,
) -> tuple[list[tuple[Loan, Book]], list[tuple[Loan, Book]]]:
    """Return current-user active loans and history with book summaries."""

    rows = db.execute(
        select(Loan, Book)
        .join(Book, Book.id == Loan.book_id)
        .where(Loan.user_id == user_id)
        .order_by(Loan.returned_at.is_(None).desc(), Loan.borrowed_at.desc(), Loan.id.desc())
    ).all()
    active: list[tuple[Loan, Book]] = []
    history: list[tuple[Loan, Book]] = []
    for loan, book in rows:
        (active if loan.returned_at is None else history).append((loan, book))
    return active, history


def serialize_loan(loan: Loan, book: Book) -> dict[str, object]:
    """Serialize a loan without exposing unrelated user or model fields."""

    return {
        "id": loan.id,
        "user_id": loan.user_id,
        "book_id": loan.book_id,
        "book_title": book.title,
        "book_author": book.author,
        "borrowed_at": loan.borrowed_at,
        "due_at": loan.due_at,
        "returned_at": loan.returned_at,
    }


def loan_book(db: Session, loan: Loan) -> Book:
    """Load the catalog row for a just-created or returned loan."""

    book = db.get(Book, loan.book_id)
    if book is None:
        raise LoanNotFound
    return book
