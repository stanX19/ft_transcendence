"""Immediate friendship operations and presence-aware list queries."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.friends.models import Friendship
from app.features.users.models import User


class FriendNotFound(Exception):
    """Raised when a requested friend or friendship does not exist."""


class FriendConflict(Exception):
    """Raised for self-friendship or a duplicate friendship."""


def _pair(first_id: int, second_id: int) -> tuple[int, int]:
    return min(first_id, second_id), max(first_id, second_id)


def add_friend(db: Session, *, user_id: int, friend_id: int) -> Friendship:
    """Create an immediate canonical friendship after validating both users."""

    if user_id == friend_id:
        raise FriendConflict
    if db.get(User, friend_id) is None:
        raise FriendNotFound
    low_id, high_id = _pair(user_id, friend_id)
    if db.scalar(
        select(Friendship).where(
            Friendship.user_low_id == low_id,
            Friendship.user_high_id == high_id,
        )
    ) is not None:
        raise FriendConflict
    friendship = Friendship(user_low_id=low_id, user_high_id=high_id)
    db.add(friendship)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise FriendConflict from None
    db.refresh(friendship)
    return friendship


def remove_friend(db: Session, *, user_id: int, friend_id: int) -> None:
    """Remove only the exact friendship owned by the current user."""

    if user_id == friend_id:
        raise FriendConflict
    if db.get(User, friend_id) is None:
        raise FriendNotFound
    low_id, high_id = _pair(user_id, friend_id)
    friendship = db.scalar(
        select(Friendship).where(
            Friendship.user_low_id == low_id,
            Friendship.user_high_id == high_id,
        )
    )
    if friendship is None:
        raise FriendNotFound
    db.delete(friendship)
    db.commit()


def list_friends(db: Session, *, user_id: int) -> list[User]:
    """Return public friend users in stable display-name order."""

    return list(
        db.scalars(
            select(User)
            .join(
                Friendship,
                or_(
                    Friendship.user_low_id == User.id,
                    Friendship.user_high_id == User.id,
                ),
            )
            .where(
                or_(
                    Friendship.user_low_id == user_id,
                    Friendship.user_high_id == user_id,
                ),
                User.id != user_id,
            )
            .order_by(User.display_name, User.id)
        ).all()
    )
