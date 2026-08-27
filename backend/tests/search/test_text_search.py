"""Free-text catalog search contracts."""

from __future__ import annotations

from uuid import uuid4


def _payload(response) -> dict:
    payload = response.json()
    assert isinstance(payload, dict), response.text
    assert {"items", "page", "page_size", "total"}.issubset(payload)
    return payload


def _ids_for_query(client, query: str) -> set[int]:
    response = client.get("/api/books", params={"q": query, "page_size": 100})
    assert response.status_code == 200, response.text
    return {item["id"] for item in _payload(response)["items"]}


def test_q_searches_title_author_description_and_isbn(client, create_search_book) -> None:
    token = uuid4().hex
    title_term = f"TitleTerm{token}"
    author_term = f"AuthorTerm{token}"
    description_term = f"DescriptionTerm{token}"
    title_book = create_search_book(title=title_term)
    author_book = create_search_book(author=author_term)
    description_book = create_search_book(description=description_term)
    isbn = f"978{token[:10]}"
    isbn_book = create_search_book(isbn=isbn)

    assert title_book.id in _ids_for_query(client, title_term)
    assert author_book.id in _ids_for_query(client, author_term)
    assert description_book.id in _ids_for_query(client, description_term)
    assert isbn_book.id in _ids_for_query(client, isbn)


def test_text_search_supports_pagination(client, create_search_book) -> None:
    token = uuid4().hex
    books = [
        create_search_book(title=f"PaginationTerm{token} {index}")
        for index in range(3)
    ]
    params = {"q": f"PaginationTerm{token}", "sort": "title", "page_size": 2}

    first = client.get("/api/books", params={**params, "page": 1})
    second = client.get("/api/books", params={**params, "page": 2})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_payload = _payload(first)
    second_payload = _payload(second)
    assert first_payload["total"] == len(books)
    assert first_payload["page"] == 1
    assert second_payload["page"] == 2
    assert len(first_payload["items"]) == 2
    assert len(second_payload["items"]) == 1
    assert {
        item["id"] for item in first_payload["items"]
    }.isdisjoint({item["id"] for item in second_payload["items"]})
