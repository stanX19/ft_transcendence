"""Conservative administrator-only account management rules."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.files.models import FileAsset
from app.features.files.storage import delete_bytes
from app.features.friends.models import Friendship
from app.features.loans.models import Loan
from app.features.users.models import User, UserRole
from app.features.users.service import is_online, normalize_email, role_value


class AdminUserNotFound(Exception):
    """Raised when an administrator targets a missing account."""


class AdminUserConflict(Exception):
    """Raised when a safe account-management rule prevents the mutation."""


def admin_user_payload(user: User) -> dict[str, object]:
    """Serialize administrator-visible fields without password material."""

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "role": role_value(user),
        "is_online": is_online(user),
        "created_at": user.created_at,
    }


def list_admin_users(
    db: Session,
    *,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    """List account records with pagination and bounded display-name search."""

    statement = select(User)
    normalized_query = query.strip()
    if normalized_query:
        statement = statement.where(
            User.display_name.ilike(f"%{normalized_query}%")
            | User.email.ilike(f"%{normalized_query}%")
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    users = list(
        db.scalars(
            statement.order_by(User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return users, total


def get_admin_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AdminUserNotFound
    return user


def update_admin_user(
    db: Session,
    user: User,
    *,
    email: str | None,
    display_name: str | None,
    bio: str | None,
) -> User:
    """Apply only supplied account fields while preserving the role boundary."""

    if email is not None:
        normalized_email = normalize_email(email)
        duplicate = db.scalar(
            select(User).where(User.email == normalized_email, User.id != user.id)
        )
        if duplicate is not None:
            raise AdminUserConflict
        user.email = normalized_email
    if display_name is not None:
        user.display_name = display_name
    if bio is not None:
        user.bio = bio
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AdminUserConflict from None
    db.refresh(user)
    return user


def _admin_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
        )
        or 0
    )


def change_admin_role(
    db: Session,
    user: User,
    *,
    actor_user_id: int,
    role: UserRole,
) -> User:
    """Change another user's role without allowing accidental admin lockout."""

    if user.id == actor_user_id:
        raise AdminUserConflict
    if user.role == UserRole.ADMIN and role != UserRole.ADMIN and _admin_count(db) <= 1:
        raise AdminUserConflict
    user.role = role
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AdminUserConflict from None
    db.refresh(user)
    return user


def delete_admin_user(db: Session, user: User, *, actor_user_id: int) -> None:
    """Delete a safe target and clean owned relationships and bytes."""

    if user.id == actor_user_id:
        raise AdminUserConflict
    if user.role == UserRole.ADMIN and _admin_count(db) <= 1:
        raise AdminUserConflict
    if db.scalar(
        select(Loan.id).where(Loan.user_id == user.id).limit(1)
    ) is not None:
        raise AdminUserConflict

    owned_assets = list(
        db.scalars(select(FileAsset).where(FileAsset.owner_user_id == user.id)).all()
    )
    friendships = list(
        db.scalars(
            select(Friendship).where(
                (Friendship.user_low_id == user.id)
                | (Friendship.user_high_id == user.id)
            )
        ).all()
    )
    for friendship in friendships:
        db.delete(friendship)
    for asset in owned_assets:
        db.delete(asset)
    db.flush()
    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AdminUserConflict from None
    for asset in owned_assets:
        delete_bytes(asset.stored_filename)
