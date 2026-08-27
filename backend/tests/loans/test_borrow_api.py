"""Authenticated borrow endpoint contracts."""

from __future__ import annotations


def test_unauthenticated_borrow_is_rejected(client, create_loan_book) -> None:
    book = create_loan_book()

    response = client.post(f"/api/books/{book.id}/borrow")

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthenticated"


def test_authenticated_borrow_and_duplicate_are_handled(
    client,
    register_user,
    create_loan_book,
) -> None:
    registration = register_user(client, display_name="Borrowing Member")
    assert registration.status_code == 201, registration.text
    book = create_loan_book(total_copies=2, available_copies=2)

    first = client.post(f"/api/books/{book.id}/borrow")
    assert first.status_code == 201, first.text
    assert first.json()["loan"]["book_id"] == book.id
    assert first.json()["loan"]["returned_at"] is None

    duplicate = client.post(f"/api/books/{book.id}/borrow")
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "conflict"


def test_zero_stock_borrow_returns_conflict(
    client,
    register_user,
    create_loan_book,
) -> None:
    registration = register_user(client, display_name="Empty Stock Member")
    assert registration.status_code == 201, registration.text
    book = create_loan_book(total_copies=1, available_copies=0)

    response = client.post(f"/api/books/{book.id}/borrow")

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"
