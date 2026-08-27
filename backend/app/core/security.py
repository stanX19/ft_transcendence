"""Password hashing and signed browser-session JWT helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings


_password_hash = PasswordHash.recommended()
# Keep an Argon2 hash available for unknown-email logins so those failures do
# not skip the password work performed for an existing account.
_DUMMY_PASSWORD_HASH = _password_hash.hash("libraryos-credential-check")


def hash_password(password: str) -> str:
    """Hash a password with pwdlib's recommended Argon2 configuration."""

    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify credentials safely, including malformed legacy hashes."""

    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def password_hash_for_login(password_hash: str | None) -> str:
    """Return a real hash for every login attempt, including unknown users."""

    return password_hash or _DUMMY_PASSWORD_HASH


def create_access_token(
    data: Mapping[str, Any],
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Sign a JWT containing the supplied claims and an explicit expiry."""

    expires = expires_delta or timedelta(hours=get_settings().auth_session_hours)
    now = datetime.now(timezone.utc)
    payload = dict(data)
    payload.update({"iat": now, "exp": now + expires})
    return jwt.encode(payload, get_settings().auth_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode a session JWT, returning ``None`` for expired/tampered tokens."""

    try:
        claims = jwt.decode(
            token,
            get_settings().auth_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    return claims if isinstance(claims, dict) else None
