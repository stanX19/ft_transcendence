"""Public API catalog update contracts."""

from __future__ import annotations


def test_public_put_updates_real_book_and_preserves_inventory(
    client,
    create_book,
    db_session,
    public_headers,
) -> None:
    book = create_book(
        title="Public Update Before",
        total_copies=5,
        available_copies=3,
    )

    response = client.put(
        f"/public-api/v1/books/{book.id}",
        json={"title": "Public Update After", "total_copies": 7},
        headers=public_headers,
    )

    assert response.status_code == 200, response.text
    updated = response.json()["book"]
    assert updated["title"] == "Public Update After"
    assert updated["total_copies"] == 7
    assert updated["available_copies"] == 5

    db_session.expire_all()
    refreshed = db_session.get(type(book), book.id)
    assert refreshed is not None
    assert refreshed.title == "Public Update After"


def test_public_patch_rejects_inventory_that_discards_borrowed_copies(
    client,
    create_book,
    public_headers,
) -> None:
    book = create_book(
        title="Public Update Conflict",
        total_copies=5,
        available_copies=3,
    )

    response = client.patch(
        f"/public-api/v1/books/{book.id}",
        json={"total_copies": 1},
        headers=public_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"
