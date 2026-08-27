"""Authenticated current-user loan tool contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


def _make_user(db_session):
    from app.features.users.models import User, UserRole

    user = User(
        email=f"ai-tool-{uuid4().hex}@example.test",
        password_hash="test-only-hash",
        display_name="AI Tool User",
        bio="",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_current_user_loans_uses_authenticated_identity(db_session, create_ai_book) -> None:
    from app.features.ai.tools import get_current_user_loans
    from app.features.loans.models import Loan

    user = _make_user(db_session)
    other = _make_user(db_session)
    book = create_ai_book()
    loan = Loan(
        user_id=user.id,
        book_id=book.id,
        borrowed_at=datetime.now(timezone.utc),
        due_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db_session.add(loan)
    db_session.commit()

    result = get_current_user_loans(db_session, user)

    assert [item["id"] for item in result["active"]] == [loan.id]
    assert get_current_user_loans(db_session, other)["active"] == []


def test_tool_dispatch_rejects_model_selected_private_user_id(db_session) -> None:
    from app.features.ai.tools import ToolAuthorizationError, ToolContext, execute_tool

    user = _make_user(db_session)
    with pytest.raises(ToolAuthorizationError):
        execute_tool(
            "get_current_user_loans",
            {"user_id": user.id + 1},
            ToolContext(db=db_session, current_user=user),
        )
