"""Privileged catalog create and inventory initialization contracts."""

from __future__ import annotations

from uuid import uuid4


def _book_payload(response) -> dict:
    payload = response.json()
    return payload.get("book", payload)


def _create_payload(label: str) -> dict:
    token = uuid4().hex
    return {
        "isbn": f"978{token[:10]}",
        "slug": f"create-{token}",
        "title": f"{label} Created Book",
        "author": f"{label} Author",
        "description": f"{label} description for create tests.",
        "category": "Create Testing",
        "publication_year": 2025,
        "total_copies": 4,
    }


def test_member_cannot_create_a_book(client, register_user) -> None:
    registration = register_user(client, display_name="Catalog Member")
    assert registration.status_code == 201, registration.text

    response = client.post("/api/books", json=_create_payload("Member"))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_librarian_and_admin_can_create_books_and_server_sets_availability(role_client) -> None:
    for role in ("LIBRARIAN", "ADMIN"):
        client = role_client(role)
        payload = _create_payload(role)
        payload["available_copies"] = 0

        response = client.post("/api/books", json=payload)

        assert response.status_code == 201, response.text
        book = _book_payload(response)
        assert book["title"] == payload["title"]
        assert book["total_copies"] == payload["total_copies"]
        assert book["available_copies"] == payload["total_copies"]


def test_create_rejects_invalid_inventory_and_duplicate_isbn(role_client) -> None:
    client = role_client("LIBRARIAN")
    invalid = _create_payload("Invalid")
    invalid["total_copies"] = -1

    invalid_response = client.post("/api/books", json=invalid)

    assert invalid_response.status_code == 422, invalid_response.text
    assert invalid_response.json()["error"]["code"] == "validation_error"

    valid = _create_payload("Duplicate")
    first = client.post("/api/books", json=valid)
    assert first.status_code == 201, first.text

    duplicate_payload = {
        **valid,
        "slug": f"{valid['slug']}-different",
        "title": f"{valid['title']} Different",
    }
    duplicate = client.post("/api/books", json=duplicate_payload)

    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "conflict"
