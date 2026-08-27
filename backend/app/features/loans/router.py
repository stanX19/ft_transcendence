"""Authenticated borrow, return, and current-user loan endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.loans.schemas import LoanEnvelope, LoanResponse, MyLoansResponse
from app.features.loans.service import (
    BookNotFound,
    BookUnavailable,
    LoanAlreadyActive,
    LoanForbidden,
    LoanNotFound,
    borrow_book,
    list_user_loans,
    loan_book,
    return_loan,
    serialize_loan,
)
from app.features.users.models import User
from app.features.users.service import role_value


router = APIRouter(tags=["loans"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT)


@router.post(
    "/api/books/{book_id}/borrow",
    response_model=LoanEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def borrow(
    book_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanEnvelope:
    try:
        loan = borrow_book(db, user_id=current_user.id, book_id=book_id)
    except BookNotFound:
        raise _not_found() from None
    except (BookUnavailable, LoanAlreadyActive, IntegrityError):
        db.rollback()
        raise _conflict() from None
    book = loan_book(db, loan)
    return LoanEnvelope(loan=LoanResponse.model_validate(serialize_loan(loan, book)))


@router.post(
    "/api/loans/{loan_id}/return",
    response_model=LoanEnvelope,
)
def return_book(
    loan_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanEnvelope:
    try:
        loan = return_loan(
            db,
            loan_id,
            actor_user_id=current_user.id,
            actor_role=role_value(current_user),
        )
    except LoanNotFound:
        raise _not_found() from None
    except LoanForbidden:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from None
    except IntegrityError:
        db.rollback()
        raise _conflict() from None
    book = loan_book(db, loan)
    return LoanEnvelope(loan=LoanResponse.model_validate(serialize_loan(loan, book)))


@router.get("/api/loans/me", response_model=MyLoansResponse)
def my_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MyLoansResponse:
    active, history = list_user_loans(db, user_id=current_user.id)
    return MyLoansResponse(
        active=[LoanResponse.model_validate(serialize_loan(loan, book)) for loan, book in active],
        history=[LoanResponse.model_validate(serialize_loan(loan, book)) for loan, book in history],
    )
