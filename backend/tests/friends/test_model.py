"""Canonical unordered friendship model contracts."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


def test_friendship_model_uses_canonical_pair_and_constraints() -> None:
    from app.core.model_registry import Base
    from app.features.friends.models import Friendship

    assert Friendship.__table__ is Base.metadata.tables["friendships"]
    assert {"user_low_id", "user_high_id"}.issubset(Friendship.__table__.c.keys())
    assert any(constraint.name == "ck_friendships_low_before_high" for constraint in Friendship.__table__.constraints)
    assert any(constraint.name == "uq_friendships_pair" for constraint in Friendship.__table__.constraints)


def test_friendship_database_rejects_self_and_duplicate_pairs(
    db_session,
    unique_email,
) -> None:
    from app.features.friends.models import Friendship
    from app.features.users.models import User

    first = User(
        email=unique_email("friend-one"),
        password_hash="test-hash",
        display_name="Friend One",
    )
    second = User(
        email=unique_email("friend-two"),
        password_hash="test-hash",
        display_name="Friend Two",
    )
    db_session.add_all([first, second])
    db_session.commit()
    db_session.refresh(first)
    db_session.refresh(second)
    db_session.add(Friendship(user_low_id=min(first.id, second.id), user_high_id=max(first.id, second.id)))
    db_session.commit()
    db_session.add(Friendship(user_low_id=max(first.id, second.id), user_high_id=min(first.id, second.id)))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    db_session.add(Friendship(user_low_id=first.id, user_high_id=first.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
