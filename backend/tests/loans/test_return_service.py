"""Idempotent return service contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_return_increments_inventory_once_and_repeat_is_noop(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.service import borrow_book, return_loan

    user = create_loan_user()
    book = create_loan_book(total_copies=1, available_copies=1)
    loan = borrow_book(db_session, user_id=user.id, book_id=book.id)
    returned_at = datetime(2024, 3, 1, tzinfo=timezone.utc)

    returned = return_loan(
        db_session,
        loan.id,
        actor_user_id=user.id,
        actor_role="MEMBER",
        returned_at=returned_at,
    )
    assert returned.returned_at == returned_at
    db_session.refresh(book)
    assert book.available_copies == 1

    repeated = return_loan(
        db_session,
        loan.id,
        actor_user_id=user.id,
        actor_role="MEMBER",
        returned_at=datetime(2024, 3, 2, tzinfo=timezone.utc),
    )
    assert repeated.returned_at == returned_at
    db_session.refresh(book)
    assert book.available_copies == 1


def test_return_requires_owner_or_privileged_role(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.service import LoanForbidden, borrow_book, return_loan

    owner = create_loan_user(display_name="Loan Owner")
    other = create_loan_user(display_name="Other Member")
    book = create_loan_book()
    loan = borrow_book(db_session, user_id=owner.id, book_id=book.id)

    with pytest.raises(LoanForbidden):
        return_loan(
            db_session,
            loan.id,
            actor_user_id=other.id,
            actor_role="MEMBER",
        )

    db_session.refresh(book)
    assert book.available_copies == 1
