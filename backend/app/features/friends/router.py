"""Authenticated immediate add/remove/list friendship endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.friends.service import (
    FriendConflict,
    FriendNotFound,
    add_friend,
    list_friends,
    remove_friend,
)
from app.features.users.models import User
from app.features.users.service import public_user_payload


router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.get("")
def read_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    return {"items": [public_user_payload(user) for user in list_friends(db, user_id=current_user.id)]}


@router.post("/{user_id}", status_code=status.HTTP_201_CREATED)
def create_friend(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        add_friend(db, user_id=current_user.id, friend_id=user_id)
    except FriendNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    except FriendConflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from None
    return {"message": "Friend added."}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_friend(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        remove_friend(db, user_id=current_user.id, friend_id=user_id)
    except FriendNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    except FriendConflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from None
