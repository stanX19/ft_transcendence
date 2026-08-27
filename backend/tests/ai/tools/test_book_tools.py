"""Book details and inventory tool contracts."""

from __future__ import annotations


def test_book_tools_reflect_current_catalog_state(db_session, create_ai_book) -> None:
    from app.features.ai.tools import get_book_availability, get_book_details

    book = create_ai_book(total_copies=4)
    details = get_book_details(db_session, book.id)
    availability = get_book_availability(db_session, book.id)

    assert details is not None
    assert details["book_id"] == book.id
    assert availability == {
        "book_id": book.id,
        "title": book.title,
        "available_copies": 4,
        "total_copies": 4,
        "available": True,
    }


def test_book_tools_return_none_for_missing_book(db_session) -> None:
    from app.features.ai.tools import get_book_availability, get_book_details

    assert get_book_details(db_session, 2147483647) is None
    assert get_book_availability(db_session, 2147483647) is None
