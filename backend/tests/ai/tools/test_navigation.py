"""Safe assistant navigation tool contracts."""

from __future__ import annotations

import pytest


def test_navigation_tool_returns_a_valid_book_route(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.tools import navigate_to_page

    book = create_ai_book(title="Navigation source book")

    assert navigate_to_page(
        db_session,
        "  BOOK ",
        book_id=book.id,
    ) == {
        "action": "navigate",
        "destination": "book",
        "path": f"/books/{book.id}",
        "book_id": book.id,
    }


def test_navigation_tool_supports_only_known_internal_pages(db_session) -> None:
    from app.features.ai.tools import ToolInputError, navigate_to_page

    assert navigate_to_page(db_session, "catalog") == {
        "action": "navigate",
        "destination": "catalog",
        "path": "/books",
    }
    assert navigate_to_page(db_session, "loans")["path"] == "/loans"
    assert navigate_to_page(db_session, "friends")["path"] == "/friends"

    with pytest.raises(ToolInputError):
        navigate_to_page(db_session, "https://example.com")


def test_navigation_tool_rejects_missing_or_unknown_books(
    db_session,
) -> None:
    from app.features.ai.tools import ToolInputError, navigate_to_page

    with pytest.raises(ToolInputError):
        navigate_to_page(db_session, "book")
    with pytest.raises(ToolInputError):
        navigate_to_page(db_session, "book", book_id=2147483647)


@pytest.mark.parametrize("invalid_id", [1.5, True, float("inf"), 10**100])
def test_navigation_tool_rejects_non_integral_book_ids(
    invalid_id,
) -> None:
    from app.features.ai.tools import ToolInputError, _book_id

    with pytest.raises(ToolInputError):
        _book_id(invalid_id)


def test_navigation_action_shape_has_one_canonical_internal_route() -> None:
    from app.features.ai.tools import canonical_navigation_action

    action = {
        "action": "navigate",
        "destination": "book",
        "path": "/books/14",
        "book_id": 14,
    }

    assert canonical_navigation_action(action) == action
    assert canonical_navigation_action({**action, "path": "/books/2147483648"}) is None
    assert canonical_navigation_action({**action, "book_id": True}) is None
