"""Documented, API-key protected catalog endpoints for integrations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.books.schemas import (
    BookCreate,
    BookEnvelope,
    BookListResponse,
    BookResponse,
    BookUpdate,
    SortOption,
)
from app.features.books.service import (
    BookHasActiveLoan,
    BookInventoryConflict,
    create_book,
    delete_book,
    get_book,
    list_books,
    update_book,
)
from app.features.public_api.security import enforce_public_api_rate_limit


router = APIRouter(
    prefix="/public-api/v1",
    tags=["public API"],
    dependencies=[Depends(enforce_public_api_rate_limit)],
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT)


@router.get(
    "/books",
    response_model=BookListResponse,
    summary="List catalog books",
    description="Search and paginate catalog records using the public integration API.",
)
def read_public_books(
    q: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=120),
    available: bool | None = Query(default=None),
    sort: SortOption = Query(default="title"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> BookListResponse:
    books, total = list_books(
        db,
        q=q,
        author=author,
        category=category,
        available=available,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return BookListResponse(
        items=[BookResponse.model_validate(book) for book in books],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/books/{book_id}",
    response_model=BookEnvelope,
    summary="Get a catalog book",
    description="Return one catalog record by its numeric identifier.",
)
def read_public_book(
    book_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> BookEnvelope:
    book = get_book(db, book_id)
    if book is None:
        raise _not_found()
    return BookEnvelope(book=BookResponse.model_validate(book))


@router.post(
    "/books",
    response_model=BookEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create a catalog book",
    description="Create a catalog record using the same validation and inventory rules as the internal API.",
)
def create_public_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
) -> BookEnvelope:
    try:
        book = create_book(db, payload)
    except IntegrityError:
        db.rollback()
        raise _conflict() from None
    return BookEnvelope(book=BookResponse.model_validate(book))


@router.put(
    "/books/{book_id}",
    response_model=BookEnvelope,
    summary="Replace editable book fields",
    description="Update a catalog record while preserving borrowed-copy inventory invariants.",
)
@router.patch(
    "/books/{book_id}",
    response_model=BookEnvelope,
    summary="Update editable book fields",
    description="Partially update a catalog record while preserving borrowed-copy inventory invariants.",
)
def update_public_book(
    payload: BookUpdate,
    book_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> BookEnvelope:
    book = get_book(db, book_id)
    if book is None:
        raise _not_found()
    try:
        updated = update_book(db, book, payload)
    except BookInventoryConflict:
        db.rollback()
        raise _conflict() from None
    except IntegrityError:
        db.rollback()
        raise _conflict() from None
    return BookEnvelope(book=BookResponse.model_validate(updated))


@router.delete(
    "/books/{book_id}",
    response_model=dict[str, str],
    summary="Delete a catalog book",
    description="Delete a catalog record when it has no active loan references.",
)
def delete_public_book(
    book_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    book = get_book(db, book_id)
    if book is None:
        raise _not_found()
    try:
        delete_book(db, book)
    except BookHasActiveLoan:
        db.rollback()
        raise _conflict() from None
    except IntegrityError:
        db.rollback()
        raise _conflict() from None
    return {"message": "Book deleted."}
