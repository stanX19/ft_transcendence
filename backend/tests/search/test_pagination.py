"""Combined catalog search/filter/sort pagination contracts."""

from __future__ import annotations

from uuid import uuid4


def _payload(response) -> dict:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert {"items", "page", "page_size", "total"}.issubset(payload)
    return payload


def test_combined_query_filters_sort_and_pagination_keep_count_and_order(
    client,
    create_search_book,
) -> None:
    token = uuid4().hex
    author = f"Pagination Author {token}"
    category = f"Pagination Category {token}"
    matching = [
        create_search_book(
            title=f"Combined Page {token} {index}",
            author=author,
            category=category,
            total_copies=4,
            available_copies=2,
        )
        for index in range(5)
    ]
    excluded_author = create_search_book(
        title=f"Combined Page {token} excluded author",
        author=f"Other Author {token}",
        category=category,
        total_copies=4,
        available_copies=2,
    )
    excluded_availability = create_search_book(
        title=f"Combined Page {token} excluded unavailable",
        author=author,
        category=category,
        total_copies=4,
        available_copies=0,
    )

    params = {
        "q": f"Combined Page {token}",
        "author": author,
        "category": category,
        "available": "true",
        "sort": "title",
        "page_size": 2,
    }
    pages = [
        _payload(client.get("/api/books", params={**params, "page": page}))
        for page in (1, 2, 3)
    ]

    assert [payload["total"] for payload in pages] == [5, 5, 5]
    assert [payload["page"] for payload in pages] == [1, 2, 3]
    assert [len(payload["items"]) for payload in pages] == [2, 2, 1]
    page_ids = [item["id"] for payload in pages for item in payload["items"]]
    assert page_ids == [book.id for book in sorted(matching, key=lambda book: book.title)]
    assert excluded_author.id not in page_ids
    assert excluded_availability.id not in page_ids


def test_page_size_has_documented_upper_bound(client) -> None:
    response = client.get("/api/books", params={"page_size": 101})

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"
