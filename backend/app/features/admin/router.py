"""Administrator-only user list, edit, delete, and role routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.features.admin.schemas import (
    AdminRoleUpdate,
    AdminUserEnvelope,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.features.admin.service import (
    AdminUserConflict,
    AdminUserNotFound,
    admin_user_payload,
    change_admin_role,
    delete_admin_user,
    get_admin_user,
    list_admin_users,
    update_admin_user,
)
from app.features.users.models import User


router = APIRouter(prefix="/api/admin/users", tags=["admin"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT)


@router.get("", response_model=AdminUserListResponse)
def read_admin_users(
    query: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> AdminUserListResponse:
    del current_user
    users, total = list_admin_users(db, query=query, page=page, page_size=page_size)
    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(admin_user_payload(user)) for user in users],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{user_id}", response_model=AdminUserEnvelope)
def edit_admin_user(
    payload: AdminUserUpdate,
    user_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> AdminUserEnvelope:
    del current_user
    try:
        user = get_admin_user(db, user_id)
        updated = update_admin_user(
            db,
            user,
            email=payload.email,
            display_name=payload.display_name,
            bio=payload.bio,
        )
    except AdminUserNotFound:
        raise _not_found() from None
    except AdminUserConflict:
        raise _conflict() from None
    return AdminUserEnvelope(user=AdminUserResponse.model_validate(admin_user_payload(updated)))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_admin_user(
    user_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> None:
    try:
        user = get_admin_user(db, user_id)
        delete_admin_user(db, user, actor_user_id=current_user.id)
    except AdminUserNotFound:
        raise _not_found() from None
    except AdminUserConflict:
        raise _conflict() from None


@router.patch("/{user_id}/role", response_model=AdminUserEnvelope)
def edit_admin_role(
    payload: AdminRoleUpdate,
    user_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> AdminUserEnvelope:
    try:
        user = get_admin_user(db, user_id)
        updated = change_admin_role(
            db,
            user,
            actor_user_id=current_user.id,
            role=payload.role,
        )
    except AdminUserNotFound:
        raise _not_found() from None
    except AdminUserConflict:
        raise _conflict() from None
    return AdminUserEnvelope(user=AdminUserResponse.model_validate(admin_user_payload(updated)))
