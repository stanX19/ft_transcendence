"""Advanced catalog search, filter, sort, and combined pagination contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .test_helpers import add_book


def _items(response) -> list[dict]:
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload["items"]


def test_free_text_search_covers_title_author_description_and_isbn(client, db_session) -> None:
    token = uuid4().hex
    title = f"Astronomy Search Title {token}"
    author = f"Distinct Author {token}"
    description = f"Botany search description {token}"
    isbn = f"978{token[:10]}"
    add_book(
        db_session,
        title=title,
        author=author,
        description=description,
        isbn=isbn,
        category="Science",
    )

    for query in (title, author, description, isbn):
        assert _items(client.get("/api/books", params={"q": query}))


def test_author_category_and_availability_filters_combine(client, db_session) -> None:
    add_book(
        db_session,
        title="Filter Available",
        author="Filter Author",
        category="History",
        total_copies=2,
        available_copies=1,
    )
    add_book(
        db_session,
        title="Filter Empty",
        author="Filter Author",
        category="History",
        total_copies=2,
        available_copies=0,
    )
    response = client.get(
        "/api/books",
        params={
            "author": "Filter Author",
            "category": "History",
            "available": "true",
        },
    )
    items = _items(response)
    assert items
    assert all(item["author"] == "Filter Author" for item in items)
    assert all(item["category"] == "History" for item in items)
    assert all(item["available_copies"] > 0 for item in items)


def test_title_author_and_newest_sort_modes_are_supported(client, db_session) -> None:
    token = uuid4().hex
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    add_book(
        db_session,
        title=f"Sort Zulu {token}",
        author=f"Sort Beta {token}",
        publication_year=2020,
        created_at=base,
    )
    add_book(
        db_session,
        title=f"Sort Alpha {token}",
        author=f"Sort Alpha {token}",
        publication_year=2025,
        created_at=base + timedelta(days=1),
    )
    add_book(
        db_session,
        title=f"Sort Middle {token}",
        author=f"Sort Zulu {token}",
        publication_year=2023,
        created_at=base + timedelta(days=2),
    )

    title_items = _items(client.get("/api/books", params={"q": f"Sort {token}", "sort": "title"}))
    author_items = _items(client.get("/api/books", params={"q": f"Sort {token}", "sort": "author"}))
    newest_items = _items(client.get("/api/books", params={"q": f"Sort {token}", "sort": "newest"}))
    assert [item["title"] for item in title_items] == sorted(item["title"] for item in title_items)
    assert [item["author"] for item in author_items] == sorted(item["author"] for item in author_items)
    assert newest_items[0]["title"] == f"Sort Middle {token}"


def test_combined_search_filters_keep_count_and_page_order_consistent(client, db_session) -> None:
    token = uuid4().hex
    author = f"Combined Author {token}"
    category = f"Combined Category {token}"
    for title, available in (("Combined Alpha", 1), ("Combined Beta", 1), ("Combined Gamma", 0)):
        add_book(
            db_session,
            title=f"{title} {token}",
            author=author,
            category=category,
            total_copies=1,
            available_copies=available,
        )

    response = client.get(
        "/api/books",
        params={
            "q": f"Combined {token}",
            "author": author,
            "category": category,
            "available": "true",
            "sort": "title",
            "page": 2,
            "page_size": 1,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == f"Combined Beta {token}"
