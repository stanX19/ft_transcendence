"""Cookie-backed account registration, login, logout, and current-user APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    password_hash_for_login,
    verify_password,
)
from app.features.auth.schemas import Credentials, RegisterRequest
from app.features.users.models import User, UserRole
from app.features.users.service import (
    find_by_email,
    normalize_email,
    private_user_payload,
    touch_last_seen,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_session_cookie(response: Response, token: str) -> None:
    """Set the one browser session cookie required by the application contract."""

    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.auth_session_hours * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the browser session using the same cookie scope and security flags."""

    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _credentials_error() -> HTTPException:
    """Return one generic error for unknown emails and wrong passwords."""

    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Create a member account and establish its browser session."""

    email = normalize_email(str(payload.email))
    if find_by_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        bio="",
        role=UserRole.MEMBER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The unique constraint is authoritative for simultaneous signups.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from None
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    set_session_cookie(response, token)
    return {"user": private_user_payload(user)}


@router.post("/login")
def login(
    payload: Credentials,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Authenticate with a normalized email and generic credential failures."""

    user = find_by_email(db, normalize_email(str(payload.email)))
    if not verify_password(
        payload.password,
        password_hash_for_login(user.password_hash if user else None),
    ):
        raise _credentials_error()
    if user is None:
        raise _credentials_error()

    touch_last_seen(db, user)
    token = create_access_token({"sub": str(user.id)})
    set_session_cookie(response, token)
    return {"user": private_user_payload(user)}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    """Return the authenticated account without password or timestamp internals."""

    return {"user": private_user_payload(current_user)}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Clear the browser session cookie; no server-side token is retained."""

    clear_session_cookie(response)
    return {"message": "Logged out."}
