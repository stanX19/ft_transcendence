"""FastAPI dependencies for database-backed authentication and authorization."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.features.users.models import User, UserRole
from app.features.users.service import touch_last_seen


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve and touch the user represented by the secure session cookie."""

    from app.core.config import get_settings

    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    claims = decode_access_token(token)
    subject = claims.get("sub") if claims else None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    touch_last_seen(db, user)
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve a session when present without making public file reads private."""

    from app.core.config import get_settings

    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        return None
    claims = decode_access_token(token)
    subject = claims.get("sub") if claims else None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None
    if user_id <= 0:
        return None
    return db.scalar(select(User).where(User.id == user_id))


def require_roles(*roles: str):
    """Build a dependency that permits only the listed backend roles."""

    allowed = {
        role.value if isinstance(role, UserRole) else str(role).upper()
        for role in roles
    }

    def role_guard(current_user: User = Depends(get_current_user)) -> User:
        actual_role = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role).upper()
        )
        if actual_role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return current_user

    return role_guard
