"""Privileged catalog update and inventory-preservation contracts."""

from __future__ import annotations


def _book_payload(response) -> dict:
    payload = response.json()
    return payload.get("book", payload)


def test_member_cannot_update_a_book(client, register_user, create_book) -> None:
    registration = register_user(client, display_name="Catalog Update Member")
    assert registration.status_code == 201, registration.text
    book = create_book(title="Member Update Target")

    response = client.patch(
        f"/api/books/{book.id}",
        json={"title": "Unauthorized Update"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_privileged_update_changes_allowed_fields(role_client, create_book) -> None:
    client = role_client("LIBRARIAN")
    book = create_book(title="Original Update Title")

    response = client.patch(
        f"/api/books/{book.id}",
        json={"title": "Updated Catalog Title", "description": "Updated details."},
    )

    assert response.status_code == 200, response.text
    updated = _book_payload(response)
    assert updated["id"] == book.id
    assert updated["title"] == "Updated Catalog Title"
    assert updated["description"] == "Updated details."
    assert updated["available_copies"] == book.available_copies


def test_total_copy_update_preserves_borrowed_count_and_rejects_too_small_total(
    role_client,
    create_book,
) -> None:
    client = role_client("ADMIN")
    book = create_book(
        title="Inventory Preservation Target",
        total_copies=5,
        available_copies=3,
    )

    increased = client.patch(
        f"/api/books/{book.id}",
        json={"total_copies": 7, "available_copies": 0},
    )

    assert increased.status_code == 200, increased.text
    increased_book = _book_payload(increased)
    assert increased_book["total_copies"] == 7
    assert increased_book["available_copies"] == 5

    too_small = client.patch(
        f"/api/books/{book.id}",
        json={"total_copies": 1},
    )

    assert too_small.status_code == 409, too_small.text
    assert too_small.json()["error"]["code"] == "conflict"


def test_update_rejects_negative_inventory(role_client, create_book) -> None:
    client = role_client("LIBRARIAN")
    book = create_book(title="Negative Inventory Target")
    response = client.patch(
        f"/api/books/{book.id}",
        json={"total_copies": -1},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"
