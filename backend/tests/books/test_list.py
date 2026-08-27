"""Catalog list and pagination contracts."""

from __future__ import annotations

from uuid import uuid4

from .test_helpers import add_book


def test_list_returns_real_books_and_stable_pagination_metadata(client, db_session) -> None:
    marker = uuid4().hex
    book = add_book(db_session, title=f"List Contract Marker {marker}")

    response = client.get(
        "/api/books",
        params={"q": f"List Contract Marker {marker}", "page": 1, "page_size": 1},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total"] >= 1
    assert payload["items"][0]["id"] == book.id
