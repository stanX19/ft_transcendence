"""Current-user loan list contracts."""

from __future__ import annotations


def test_my_loans_separates_active_and_history_for_current_user(
    client,
    register_user,
    create_loan_book,
) -> None:
    registration = register_user(client, display_name="My Loans Reader")
    assert registration.status_code == 201, registration.text
    active_book = create_loan_book(title="Active My Loans Book")
    history_book = create_loan_book(title="History My Loans Book")

    active_borrow = client.post(f"/api/books/{active_book.id}/borrow")
    history_borrow = client.post(f"/api/books/{history_book.id}/borrow")
    assert active_borrow.status_code == 201, active_borrow.text
    assert history_borrow.status_code == 201, history_borrow.text
    history_loan_id = history_borrow.json()["loan"]["id"]
    assert client.post(f"/api/loans/{history_loan_id}/return").status_code == 200

    response = client.get("/api/loans/me")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [loan["book_id"] for loan in payload["active"]] == [active_book.id]
    assert payload["active"][0]["book_title"] == "Active My Loans Book"
    assert [loan["book_id"] for loan in payload["history"]] == [history_book.id]
    assert payload["history"][0]["returned_at"] is not None
