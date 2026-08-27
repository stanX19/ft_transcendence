"""Authenticated people directory and public/own profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.users.schemas import UserDirectoryResponse, UserProfileUpdate
from app.features.users.service import (
    private_user_payload,
    public_user_payload,
    search_public_users,
    update_profile,
)
from app.features.users.models import User


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserDirectoryResponse)
def list_users(
    query: str = Query(default="", max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Find people by display name without exposing account-private fields."""

    del current_user
    users, total = search_public_users(
        db,
        query=query,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [public_user_payload(user) for user in users],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{user_id}")
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return the public profile for any existing user."""

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"user": public_user_payload(user)}


@router.patch("/me")
def patch_own_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Update only the authenticated user's public profile fields."""

    updated = update_profile(
        db,
        current_user,
        display_name=payload.display_name,
        bio=payload.bio,
    )
    return {"user": private_user_payload(updated)}
