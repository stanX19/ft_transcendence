"""Pydantic response contracts for loans."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LoanResponse(BaseModel):
    """A loan plus the small book summary needed by the account UI."""

    id: int
    user_id: int
    book_id: int
    book_title: str
    book_author: str
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None


class LoanEnvelope(BaseModel):
    loan: LoanResponse


class MyLoansResponse(BaseModel):
    active: list[LoanResponse]
    history: list[LoanResponse]
