"""Loan schema, foreign-key, and active-loan uniqueness contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError


def test_loan_model_is_registered_with_required_relationship_fields() -> None:
    from app.core.model_registry import Base
    from app.features.loans.models import Loan

    assert Loan.__table__ is Base.metadata.tables["loans"]
    columns = inspect(Loan.__table__).columns
    assert {
        "id",
        "user_id",
        "book_id",
        "borrowed_at",
        "due_at",
        "returned_at",
    }.issubset(columns.keys())
    foreign_keys = {
        foreign_key.target_fullname for foreign_key in Loan.__table__.foreign_keys
    }
    assert "users.id" in foreign_keys
    assert "books.id" in foreign_keys
    assert columns["returned_at"].nullable is True


def test_only_one_active_loan_per_user_and_book_is_allowed(
    db_session,
    create_loan_user,
    create_loan_book,
) -> None:
    from app.features.loans.models import Loan

    user = create_loan_user()
    book = create_loan_book(total_copies=2)
    borrowed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    first = Loan(
        user_id=user.id,
        book_id=book.id,
        borrowed_at=borrowed_at,
        due_at=borrowed_at + timedelta(days=14),
    )
    db_session.add(first)
    db_session.commit()

    duplicate = Loan(
        user_id=user.id,
        book_id=book.id,
        borrowed_at=borrowed_at + timedelta(minutes=1),
        due_at=borrowed_at + timedelta(days=14, minutes=1),
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    returned = Loan(
        user_id=user.id,
        book_id=book.id,
        borrowed_at=borrowed_at + timedelta(minutes=2),
        due_at=borrowed_at + timedelta(days=14, minutes=2),
        returned_at=borrowed_at + timedelta(days=1),
    )
    db_session.add(returned)
    db_session.commit()
