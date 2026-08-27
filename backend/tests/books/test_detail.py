"""Catalog detail contracts."""

from __future__ import annotations

from .test_helpers import add_book


def test_existing_book_detail_returns_catalog_fields(client, db_session) -> None:
    book = add_book(db_session, title="Detail Contract Marker", total_copies=4, available_copies=4)

    response = client.get(f"/api/books/{book.id}")

    assert response.status_code == 200, response.text
    payload = response.json().get("book", response.json())
    assert payload["id"] == book.id
    assert payload["title"] == "Detail Contract Marker"
    assert payload["available_copies"] == 4


def test_missing_book_detail_returns_not_found(client) -> None:
    response = client.get("/api/books/2147483647")

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"
