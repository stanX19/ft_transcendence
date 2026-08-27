"""Public API catalog deletion contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4


def test_public_delete_removes_safe_book(
    client,
    create_book,
    public_headers,
) -> None:
    book = create_book(title="Public Delete Marker")

    response = client.delete(
        f"/public-api/v1/books/{book.id}",
        headers=public_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Book deleted."
    missing = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
    assert missing.status_code == 404, missing.text


def test_public_delete_rejects_book_with_active_loan(
    client,
    create_book,
    db_session,
    public_headers,
) -> None:
    from app.features.loans.models import Loan
    from app.features.users.models import User, UserRole

    user = User(
        email=f"public-delete-{uuid4().hex}@example.test",
        password_hash="test-only-hash",
        display_name="Public Delete Loan User",
        bio="",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.flush()
    book = create_book(
        title="Public Active Loan Delete Marker",
        total_copies=1,
        available_copies=0,
    )
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

    response = client.delete(
        f"/public-api/v1/books/{book.id}",
        headers=public_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"
