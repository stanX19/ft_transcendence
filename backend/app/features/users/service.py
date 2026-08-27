"""Small user/profile service shared by the users and auth routers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.users.models import User, UserRole


def normalize_email(email: str) -> str:
    """Normalize the identity used for both persistence and login lookup."""

    return email.strip().lower()


def is_online(user: User) -> bool:
    """Determine presence from the configured short activity threshold."""

    if user.last_seen_at is None:
        return False

    last_seen = user.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - last_seen).total_seconds()
    return age_seconds <= get_settings().online_threshold_seconds


def role_value(user: User) -> str:
    """Return a stable JSON role value for either enum or string instances."""

    role = user.role
    return role.value if isinstance(role, UserRole) else str(role)


def private_user_payload(user: User) -> dict[str, object]:
    """Serialize account-owner fields without password or timestamp internals."""

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "role": role_value(user),
        "is_online": is_online(user),
    }


def public_user_payload(user: User) -> dict[str, object]:
    """Serialize only fields intended to be visible on a public profile."""

    return {
        "id": user.id,
        "display_name": user.display_name,
        "bio": user.bio,
        "is_online": is_online(user),
    }


def find_by_email(db: Session, email: str) -> User | None:
    """Find an account by its already-normalized email."""

    return db.scalar(select(User).where(User.email == normalize_email(email)))


def touch_last_seen(db: Session, user: User) -> None:
    """Persist activity for an authenticated request."""

    user.last_seen_at = datetime.now(timezone.utc)
    db.commit()


def update_profile(db: Session, user: User, *, display_name: str | None, bio: str | None) -> User:
    """Apply only explicitly supplied own-profile fields."""

    if display_name is not None:
        user.display_name = display_name
    if bio is not None:
        user.bio = bio
    db.commit()
    db.refresh(user)
    return user


def search_public_users(
    db: Session,
    *,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    """Search display names and return public users with stable pagination."""

    statement = select(User)
    normalized_query = query.strip()
    if normalized_query:
        terms = [term for term in normalized_query.split() if term]
        for term in terms:
            statement = statement.where(User.display_name.ilike(f"%{term}%"))

    total_statement = select(func.count()).select_from(statement.subquery())
    total = db.scalar(total_statement) or 0
    users = list(
        db.scalars(
            statement.order_by(func.lower(User.display_name), User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return users, total
