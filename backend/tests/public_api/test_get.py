"""Public API catalog read contracts."""

from __future__ import annotations

from uuid import uuid4


def test_public_get_list_reads_real_db_and_supports_catalog_filters(
    client,
    create_book,
    public_headers,
) -> None:
    marker = uuid4().hex
    book = create_book(
        title=f"Public List Marker {marker}",
        author="Public API Author",
        category="Public API",
        total_copies=3,
        available_copies=0,
    )

    response = client.get(
        "/public-api/v1/books",
        params={
            "q": f"Public List Marker {marker}",
            "author": "Public API Author",
            "category": "Public API",
            "available": "false",
            "page": 1,
            "page_size": 1,
        },
        headers=public_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == book.id
    assert payload["items"][0]["available_copies"] == 0


def test_public_get_detail_returns_real_book_and_not_found(
    client,
    create_book,
    public_headers,
) -> None:
    book = create_book(title="Public Detail Marker")

    response = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
    assert response.status_code == 200, response.text
    assert response.json()["book"]["title"] == "Public Detail Marker"

    missing = client.get("/public-api/v1/books/2147483647", headers=public_headers)
    assert missing.status_code == 404, missing.text
    assert missing.json()["error"]["code"] == "not_found"
