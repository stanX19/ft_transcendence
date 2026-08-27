"""Catalog title, author, and newest sort contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _titles(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


def test_title_sort_is_ascending(client, create_search_book) -> None:
    token = uuid4().hex
    titles = [f"Title Sort {token} C", f"Title Sort {token} A", f"Title Sort {token} B"]
    for title in titles:
        create_search_book(title=title)

    response = client.get(
        "/api/books",
        params={"q": f"Title Sort {token}", "sort": "title", "page_size": 100},
    )

    assert _titles(response) == sorted(titles)


def test_author_sort_is_ascending(client, create_search_book) -> None:
    token = uuid4().hex
    authors = [f"Z Author {token}", f"A Author {token}", f"M Author {token}"]
    for index, author in enumerate(authors):
        create_search_book(title=f"Author Sort {token} {index}", author=author)

    response = client.get(
        "/api/books",
        params={"q": f"Author Sort {token}", "sort": "author", "page_size": 100},
    )

    assert response.status_code == 200, response.text
    actual_authors = [item["author"] for item in response.json()["items"]]
    assert actual_authors == sorted(authors)


def test_newest_sort_is_descending_by_created_at(client, create_search_book) -> None:
    token = uuid4().hex
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    books = [
        create_search_book(
            title=f"Newest Sort {token} {index}",
            created_at=base + timedelta(days=index),
        )
        for index in range(3)
    ]

    response = client.get(
        "/api/books",
        params={"q": f"Newest Sort {token}", "sort": "newest", "page_size": 100},
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [
        books[2].id,
        books[1].id,
        books[0].id,
    ]
