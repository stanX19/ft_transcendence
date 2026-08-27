"""Return endpoint authorization and idempotency contracts."""

from __future__ import annotations


def test_only_owner_or_privileged_user_can_return_a_loan(
    client_factory,
    register_user,
    create_loan_book,
) -> None:
    owner = client_factory()
    owner_registration = register_user(owner, display_name="Return Owner")
    assert owner_registration.status_code == 201, owner_registration.text
    other = client_factory()
    other_registration = register_user(other, display_name="Return Other")
    assert other_registration.status_code == 201, other_registration.text
    book = create_loan_book(total_copies=1, available_copies=1)

    borrowed = owner.post(f"/api/books/{book.id}/borrow")
    assert borrowed.status_code == 201, borrowed.text
    loan_id = borrowed.json()["loan"]["id"]

    forbidden = other.post(f"/api/loans/{loan_id}/return")
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["error"]["code"] == "forbidden"

    returned = owner.post(f"/api/loans/{loan_id}/return")
    assert returned.status_code == 200, returned.text
    assert returned.json()["loan"]["returned_at"] is not None

    repeated = owner.post(f"/api/loans/{loan_id}/return")
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["loan"]["returned_at"] == returned.json()["loan"]["returned_at"]
