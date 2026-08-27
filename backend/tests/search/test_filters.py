"""Catalog author, category, availability, and combined-filter contracts."""

from __future__ import annotations

from uuid import uuid4


def _items(response) -> list[dict]:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict), response.text
    return payload["items"]


def test_author_category_and_availability_filters_work_individually(
    client,
    create_search_book,
) -> None:
    token = uuid4().hex
    author = f"Filter Author {token}"
    category = f"Filter Category {token}"
    matching = create_search_book(
        title=f"Matching Filter {token}",
        author=author,
        category=category,
        total_copies=3,
        available_copies=2,
    )
    unavailable = create_search_book(
        title=f"Unavailable Filter {token}",
        author=author,
        category=category,
        total_copies=3,
        available_copies=0,
    )
    other_author = create_search_book(
        title=f"Other Author Filter {token}",
        author=f"Other Author {token}",
        category=category,
    )
    other_category = create_search_book(
        title=f"Other Category Filter {token}",
        author=author,
        category=f"Other Category {token}",
    )

    by_author = {
        item["id"]
        for item in _items(client.get("/api/books", params={"author": author}))
    }
    by_category = {
        item["id"]
        for item in _items(client.get("/api/books", params={"category": category}))
    }
    available = {
        item["id"]
        for item in _items(
            client.get(
                "/api/books",
                params={"q": token, "available": "true", "page_size": 100},
            )
        )
    }
    unavailable_ids = {
        item["id"]
        for item in _items(
            client.get(
                "/api/books",
                params={"q": token, "available": "false", "page_size": 100},
            )
        )
    }

    assert matching.id in by_author
    assert unavailable.id in by_author
    assert other_author.id not in by_author
    assert matching.id in by_category
    assert other_category.id not in by_category
    assert matching.id in available
    assert unavailable.id not in available
    assert unavailable.id in unavailable_ids
    assert matching.id not in unavailable_ids


def test_filters_combine_with_and_semantics(client, create_search_book) -> None:
    token = uuid4().hex
    author = f"Combined Author {token}"
    category = f"Combined Category {token}"
    matching = create_search_book(
        title=f"Combined Match {token}",
        author=author,
        category=category,
        total_copies=2,
        available_copies=1,
    )
    wrong_author = create_search_book(
        title=f"Combined Wrong Author {token}",
        author=f"Wrong Author {token}",
        category=category,
        total_copies=2,
        available_copies=1,
    )
    wrong_category = create_search_book(
        title=f"Combined Wrong Category {token}",
        author=author,
        category=f"Wrong Category {token}",
        total_copies=2,
        available_copies=1,
    )
    unavailable = create_search_book(
        title=f"Combined Unavailable {token}",
        author=author,
        category=category,
        total_copies=2,
        available_copies=0,
    )

    response = client.get(
        "/api/books",
        params={
            "author": author,
            "category": category,
            "available": "true",
        },
    )

    ids = {item["id"] for item in _items(response)}
    assert ids == {matching.id}
    assert wrong_author.id not in ids
    assert wrong_category.id not in ids
    assert unavailable.id not in ids
