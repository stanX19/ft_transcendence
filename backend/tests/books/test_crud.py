"""Librarian/admin catalog CRUD and inventory ownership contracts."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from .test_helpers import add_book


def _promote(db_session, email: str, role: str) -> None:
    from app.features.users.models import User

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = role
    db_session.commit()


def _book_payload(title: str = "CRUD Contract Book") -> dict[str, object]:
    return {
        "isbn": f"978{uuid4().hex[:10]}",
        "title": title,
        "author": "CRUD Author",
        "description": "A book used for catalog CRUD contracts.",
        "category": "Testing",
        "publication_year": 2024,
        "total_copies": 3,
    }


def test_member_cannot_create_update_or_delete_books(
    client,
    register_user,
    db_session,
) -> None:
    registration = register_user(client, display_name="Catalog Member")
    assert registration.status_code == 201, registration.text

    create = client.post("/api/books", json=_book_payload())
    assert create.status_code == 403, create.text


def test_librarian_can_create_and_update_server_managed_inventory(
    client_factory,
    register_user,
    db_session,
) -> None:
    setup = client_factory()
    registration = register_user(setup, display_name="Catalog Librarian")
    assert registration.status_code == 201, registration.text
    email = registration.json()["user"]["email"]
    _promote(db_session, email, "LIBRARIAN")

    librarian = client_factory()
    login = librarian.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text

    created = librarian.post("/api/books", json=_book_payload())
    assert created.status_code == 201, created.text
    book = created.json().get("book", created.json())
    assert book["available_copies"] == 3

    attempted_availability = librarian.post(
        "/api/books",
        json={**_book_payload("Client Availability"), "available_copies": 0},
    )
    assert attempted_availability.status_code == 201, attempted_availability.text
    assert attempted_availability.json().get("book", attempted_availability.json())["available_copies"] == 3

    updated = librarian.patch(
        f"/api/books/{book['id']}",
        json={"title": "Updated CRUD Contract Book", "total_copies": 5},
    )
    assert updated.status_code == 200, updated.text
    updated_book = updated.json().get("book", updated.json())
    assert updated_book["title"] == "Updated CRUD Contract Book"
    assert updated_book["available_copies"] == 5


def test_librarian_can_delete_safe_book_and_missing_delete_is_not_found(
    client_factory,
    register_user,
    db_session,
) -> None:
    setup = client_factory()
    registration = register_user(setup, display_name="Delete Librarian")
    assert registration.status_code == 201, registration.text
    email = registration.json()["user"]["email"]
    _promote(db_session, email, "ADMIN")

    admin = client_factory()
    login = admin.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text

    created = admin.post("/api/books", json=_book_payload("Delete Contract Book"))
    assert created.status_code == 201, created.text
    book_id = created.json().get("book", created.json())["id"]

    deleted = admin.delete(f"/api/books/{book_id}")
    assert deleted.status_code in (200, 204), deleted.text
    assert admin.get(f"/api/books/{book_id}").status_code == 404
    assert admin.delete("/api/books/2147483647").status_code == 404


def test_invalid_inventory_payload_is_rejected_by_catalog_api(
    client_factory,
    register_user,
    db_session,
) -> None:
    setup = client_factory()
    registration = register_user(setup, display_name="Inventory Librarian")
    assert registration.status_code == 201, registration.text
    email = registration.json()["user"]["email"]
    _promote(db_session, email, "LIBRARIAN")

    librarian = client_factory()
    assert librarian.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    ).status_code == 200
    response = librarian.post(
        "/api/books",
        json={**_book_payload("Invalid Inventory"), "total_copies": -1},
    )
    assert response.status_code == 422, response.text
