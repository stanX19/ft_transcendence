"""Safe, thin AI tools backed by the existing catalog and loan services."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.features.books import service as books_service
from app.features.loans import service as loans_service
from app.features.users.models import User


MAX_TOOL_RESULTS = 5
MAX_LOAN_RESULTS = 20
MAX_BOOK_ID = 2_147_483_647

_NAVIGATION_PATHS = {
    "catalog": "/books",
    "loans": "/loans",
    "friends": "/friends",
    "people": "/people",
    "profile": "/profile",
    "assistant": "/assistant",
}


class ToolAuthorizationError(Exception):
    """Raised when a model tries to request data outside its tool context."""


class ToolInputError(Exception):
    """Raised when a model supplies an invalid tool argument."""


@dataclass(frozen=True)
class ToolContext:
    """Request-scoped dependencies available to tool execution."""

    db: Session
    current_user: User


AuthenticatedToolContext = ToolContext


def normalize_navigation_destination(value: object) -> str:
    """Return one known destination in its canonical lowercase form."""

    if not isinstance(value, str):
        raise ToolInputError("destination must be a known LibraryOS page.")
    destination = value.strip().lower()
    if destination != "book" and destination not in _NAVIGATION_PATHS:
        raise ToolInputError("The requested LibraryOS page is not available.")
    return destination


def canonical_navigation_action(result: object) -> dict[str, object] | None:
    """Keep only the exact internal route shape accepted by the browser."""

    if not isinstance(result, Mapping):
        return None
    action = result.get("action")
    destination = result.get("destination")
    path = result.get("path")
    book_id = result.get("book_id")
    if action != "navigate" or not isinstance(destination, str) or not isinstance(path, str):
        return None
    if destination == "book":
        if type(book_id) is not int or not 1 <= book_id <= MAX_BOOK_ID:
            return None
        expected_path = f"/books/{book_id}"
    elif destination in _NAVIGATION_PATHS and book_id is None:
        expected_path = _NAVIGATION_PATHS[destination]
    else:
        return None
    if path != expected_path:
        return None
    payload: dict[str, object] = {
        "action": action,
        "destination": destination,
        "path": path,
    }
    if destination == "book":
        payload["book_id"] = book_id
    return payload


def _book_payload(book: Any) -> dict[str, object]:
    """Return only catalog fields useful to the assistant."""

    return {
        "book_id": book.id,
        "id": book.id,
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "category": book.category,
        "publication_year": book.publication_year,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
    }


def search_catalog(
    db: Session,
    query: str = "",
    *,
    q: str | None = None,
    limit: int = MAX_TOOL_RESULTS,
) -> list[dict[str, object]]:
    """Search the existing catalog service and return bounded book records."""

    search_query = query if q is None else q
    bounded_limit = max(1, min(int(limit), MAX_TOOL_RESULTS))
    books, _total = books_service.list_books(
        db,
        q=search_query.strip() or None,
        author=None,
        category=None,
        available=None,
        sort="title",
        page=1,
        page_size=bounded_limit,
    )
    return [_book_payload(book) for book in books]


def get_book_details(db: Session, book_id: int) -> dict[str, object] | None:
    """Read one catalog record through the existing book service."""

    book = books_service.get_book(db, _book_id(book_id))
    return None if book is None else _book_payload(book)


def get_book_availability(db: Session, book_id: int) -> dict[str, object] | None:
    """Read current inventory from the database-backed catalog record."""

    book = books_service.get_book(db, _book_id(book_id))
    if book is None:
        return None
    return {
        "book_id": book.id,
        "title": book.title,
        "available_copies": book.available_copies,
        "total_copies": book.total_copies,
        "available": book.available_copies > 0,
    }


def get_current_user_loans(
    db: Session,
    current_user: User,
) -> dict[str, list[dict[str, object]]]:
    """Return only the authenticated request user's loans.

    There is intentionally no user-id argument. The model receives identity
    from the request context and cannot choose another private account.
    """

    active, history = loans_service.list_user_loans(db, user_id=current_user.id)
    return {
        "active": [
            _loan_payload(loan, book)
            for loan, book in active[:MAX_LOAN_RESULTS]
        ],
        "history": [
            _loan_payload(loan, book)
            for loan, book in history[:MAX_LOAN_RESULTS]
        ],
    }


def navigate_to_page(
    db: Session,
    destination: str,
    *,
    book_id: object | None = None,
) -> dict[str, object]:
    """Return one validated internal route without performing an action."""

    target = normalize_navigation_destination(destination)
    if target == "book":
        resolved_book_id = _book_id(book_id)
        if books_service.get_book(db, resolved_book_id) is None:
            raise ToolInputError("The requested book was not found.")
        return {
            "action": "navigate",
            "destination": "book",
            "path": f"/books/{resolved_book_id}",
            "book_id": resolved_book_id,
        }
    path = _NAVIGATION_PATHS.get(target)
    if path is None or book_id is not None:
        raise ToolInputError("The requested LibraryOS page is not available.")
    return {
        "action": "navigate",
        "destination": target,
        "path": path,
    }


def _loan_payload(loan: Any, book: Any) -> dict[str, object]:
    """Make the existing loan service result JSON-safe for a model call."""

    payload = loans_service.serialize_loan(loan, book)
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in payload.items()
    }


def _book_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ToolInputError("book_id must be a positive integer.")
    if isinstance(value, str) and not value.strip().isdecimal():
        raise ToolInputError("book_id must be a positive integer.")
    try:
        book_id = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ToolInputError("book_id must be a positive integer.") from exc
    if book_id <= 0 or book_id > MAX_BOOK_ID:
        raise ToolInputError("book_id must be a positive integer.")
    return book_id


TOOL_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "name": "search_catalog",
        "description": "Search the local library catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Catalog search text."},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_RESULTS},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_book_details",
        "description": "Get details for one local catalog book.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_id": {"type": "integer", "minimum": 1, "maximum": MAX_BOOK_ID},
            },
            "required": ["book_id"],
        },
    },
    {
        "name": "get_book_availability",
        "description": "Get current physical-copy availability for one book.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_id": {"type": "integer", "minimum": 1, "maximum": MAX_BOOK_ID},
            },
            "required": ["book_id"],
        },
    },
    {
        "name": "get_current_user_loans",
        "description": "Get the authenticated user's active loans and history.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "navigate_to_page",
        "description": (
            "Navigate the user to a safe LibraryOS page. This never borrows, "
            "returns, creates, edits, or deletes anything. For borrowing a "
            "specific book, use destination 'book' with its book_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "enum": [
                        "catalog",
                        "book",
                        "loans",
                        "friends",
                        "people",
                        "profile",
                        "assistant",
                    ],
                },
                "book_id": {"type": "integer", "minimum": 1, "maximum": MAX_BOOK_ID},
            },
            "required": ["destination"],
            "additionalProperties": False,
        },
    },
)


def tool_definitions() -> list[dict[str, object]]:
    """Return a copy suitable for provider/tool configuration."""

    return [dict(definition) for definition in TOOL_DEFINITIONS]


def execute_tool(
    name: str,
    arguments: Mapping[str, object] | None,
    context: ToolContext,
) -> object:
    """Dispatch one allowlisted tool using request-scoped dependencies."""

    values = dict(arguments or {})
    if name == "search_catalog":
        return search_catalog(
            context.db,
            str(values.get("query", "")),
            limit=int(values.get("limit", MAX_TOOL_RESULTS)),
        )
    if name == "get_book_details":
        return get_book_details(context.db, _book_id(values.get("book_id")))
    if name == "get_book_availability":
        return get_book_availability(context.db, _book_id(values.get("book_id")))
    if name == "get_current_user_loans":
        if "user_id" in values or "userId" in values:
            raise ToolAuthorizationError(
                "The current-user loan tool does not accept a user id."
            )
        return get_current_user_loans(context.db, context.current_user)
    if name == "navigate_to_page":
        return navigate_to_page(
            context.db,
            str(values.get("destination", "")),
            book_id=values.get("book_id"),
        )
    raise ToolInputError("Unknown assistant tool.")


__all__ = [
    "AuthenticatedToolContext",
    "MAX_BOOK_ID",
    "MAX_LOAN_RESULTS",
    "MAX_TOOL_RESULTS",
    "TOOL_DEFINITIONS",
    "ToolAuthorizationError",
    "ToolContext",
    "ToolInputError",
    "canonical_navigation_action",
    "execute_tool",
    "get_book_availability",
    "get_book_details",
    "get_current_user_loans",
    "navigate_to_page",
    "normalize_navigation_destination",
    "search_catalog",
    "tool_definitions",
]
