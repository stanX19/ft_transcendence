"""Public API catalog creation contracts."""

from __future__ import annotations

from uuid import uuid4


def test_public_post_creates_a_real_book_with_server_owned_inventory(
    client,
    db_session,
    public_headers,
) -> None:
    from sqlalchemy import select

    from app.features.books.models import Book

    token = uuid4().hex
    payload = {
        "isbn": f"978{token[:10]}",
        "slug": f"public-{token}",
        "title": "Public Create Marker",
        "author": "Public API Author",
        "description": "Created through the API key boundary.",
        "category": "Integrations",
        "publication_year": 2025,
        "total_copies": 4,
        "available_copies": 0,
    }

    response = client.post(
        "/public-api/v1/books",
        json=payload,
        headers=public_headers,
    )

    assert response.status_code == 201, response.text
    created = response.json()["book"]
    assert created["title"] == payload["title"]
    assert created["available_copies"] == payload["total_copies"]

    persisted = db_session.scalar(select(Book).where(Book.id == created["id"]))
    assert persisted is not None
    assert persisted.title == payload["title"]


def test_public_post_uses_normal_validation_and_conflict_semantics(
    client,
    create_book,
    public_headers,
) -> None:
    token = uuid4().hex
    existing = create_book(
        title="Public Duplicate ISBN",
        isbn=f"978{token[:10]}",
    )
    invalid = client.post(
        "/public-api/v1/books",
        json={"title": "Too little"},
        headers=public_headers,
    )
    assert invalid.status_code == 422, invalid.text

    duplicate = client.post(
        "/public-api/v1/books",
        json={
            "isbn": existing.isbn,
            "title": "Public Duplicate Copy",
            "author": "Public API Author",
            "description": "Duplicate ISBN should conflict.",
            "category": "Integrations",
            "total_copies": 1,
        },
        headers=public_headers,
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "conflict"
