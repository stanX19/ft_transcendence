"""Final-copy concurrent borrowing acceptance test."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select


def test_two_users_borrowing_final_copy_yields_one_success_and_one_conflict(
    client_factory,
    register_user,
    create_loan_book,
    db_session,
) -> None:
    first_client = client_factory()
    second_client = client_factory()
    first_registration = register_user(first_client, display_name="Concurrent One")
    second_registration = register_user(second_client, display_name="Concurrent Two")
    assert first_registration.status_code == 201, first_registration.text
    assert second_registration.status_code == 201, second_registration.text
    book = create_loan_book(total_copies=1, available_copies=1)
    barrier = Barrier(2)

    def borrow(test_client):
        barrier.wait(timeout=10)
        return test_client.post(f"/api/books/{book.id}/borrow")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(borrow, (first_client, second_client)))

    assert sorted(response.status_code for response in responses) == [201, 409]
    db_session.expire_all()
    from app.features.books.models import Book
    from app.features.loans.models import Loan

    persisted_book = db_session.get(Book, book.id)
    active_loans = db_session.scalar(
        select(func.count())
        .select_from(Loan)
        .where(Loan.book_id == book.id, Loan.returned_at.is_(None))
    )
    assert persisted_book is not None
    assert persisted_book.available_copies == 0
    assert active_loans == 1
