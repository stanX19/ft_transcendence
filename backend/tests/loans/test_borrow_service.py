"""Transaction-safe borrow service contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def test_borrow_decrements_inventory_and_sets_fourteen_day_due_date(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.service import borrow_book

    user = create_loan_user()
    book = create_loan_book(total_copies=2, available_copies=2)
    borrowed_at = datetime(2024, 2, 1, 10, 30, tzinfo=timezone.utc)

    loan = borrow_book(
        db_session,
        user_id=user.id,
        book_id=book.id,
        borrowed_at=borrowed_at,
    )

    assert loan.user_id == user.id
    assert loan.book_id == book.id
    assert loan.borrowed_at == borrowed_at
    assert loan.due_at == borrowed_at + timedelta(days=14)
    db_session.refresh(book)
    assert book.available_copies == 1


def test_borrow_rejects_zero_stock_without_creating_a_loan(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.models import Loan
    from app.features.loans.service import BookUnavailable, borrow_book

    user = create_loan_user()
    book = create_loan_book(total_copies=1, available_copies=0)

    with pytest.raises(BookUnavailable):
        borrow_book(db_session, user_id=user.id, book_id=book.id)

    assert db_session.query(Loan).filter_by(book_id=book.id).count() == 0


def test_borrow_rejects_duplicate_active_loan_for_same_user_and_book(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.service import LoanAlreadyActive, borrow_book

    user = create_loan_user()
    book = create_loan_book(total_copies=2, available_copies=2)
    borrow_book(db_session, user_id=user.id, book_id=book.id)

    with pytest.raises(LoanAlreadyActive):
        borrow_book(db_session, user_id=user.id, book_id=book.id)

    db_session.refresh(book)
    assert book.available_copies == 1
