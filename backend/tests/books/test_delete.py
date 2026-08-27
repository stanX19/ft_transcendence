"""Privileged catalog delete and inventory-safety contracts."""

from __future__ import annotations


def test_member_cannot_delete_a_book(client, register_user, create_book) -> None:
    registration = register_user(client, display_name="Catalog Delete Member")
    assert registration.status_code == 201, registration.text
    book = create_book(title="Member Delete Target")

    response = client.delete(f"/api/books/{book.id}")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_librarian_can_delete_a_safe_book_and_missing_book_is_not_found(
    role_client,
    create_book,
) -> None:
    client = role_client("LIBRARIAN")
    book = create_book(title="Safe Delete Target")

    deleted = client.delete(f"/api/books/{book.id}")

    assert deleted.status_code in (200, 204), deleted.text
    missing_after_delete = client.get(f"/api/books/{book.id}")
    assert missing_after_delete.status_code == 404, missing_after_delete.text

    missing = client.delete("/api/books/2147483647")
    assert missing.status_code == 404, missing.text
    assert missing.json()["error"]["code"] == "not_found"


def test_book_with_active_loan_is_not_deleted(
    role_client,
    create_book,
    db_session,
) -> None:
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select

    from app.features.loans.models import Loan
    from app.features.users.models import User

    client = role_client("ADMIN")
    book = create_book(
        title="Active Loan Delete Target",
        total_copies=2,
        available_copies=1,
    )
    user = db_session.scalar(select(User).order_by(User.id.desc()))
    assert user is not None
    borrowed_at = datetime.now(timezone.utc)
    db_session.add(
        Loan(
            user_id=user.id,
            book_id=book.id,
            borrowed_at=borrowed_at,
            due_at=borrowed_at + timedelta(days=14),
        )
    )
    db_session.commit()

    response = client.delete(f"/api/books/{book.id}")

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"
