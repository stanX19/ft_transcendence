"""Password and browser-session security contracts."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from jwt import InvalidTokenError


COOKIE_NAME = "libraryos_session"


def _set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


def _assert_session_cookie(response) -> str:
    headers = _set_cookie_headers(response)
    cookie_header = next(
        (
            header
            for header in headers
            if header.lower().startswith(f"{COOKIE_NAME.lower()}=")
        ),
        None,
    )
    assert cookie_header is not None, headers

    attributes = cookie_header.lower()
    assert "secure" in attributes
    assert "httponly" in attributes
    assert "samesite=lax" in attributes
    assert "path=/" in attributes

    value = cookie_header.split("=", 1)[1].split(";", 1)[0]
    assert value
    return value


def test_password_hashing_is_salted_modern_and_verifiable() -> None:
    from app.core.security import hash_password, verify_password

    plaintext = "correct-horse-battery-staple"
    first_hash = hash_password(plaintext)
    second_hash = hash_password(plaintext)

    assert first_hash.startswith("$argon2")
    assert second_hash.startswith("$argon2")
    assert first_hash != second_hash
    assert plaintext not in first_hash
    assert verify_password(plaintext, first_hash)
    assert not verify_password("wrong-password", first_hash)


def test_jwt_session_utility_signs_subject_and_rejects_tampering_and_expiry() -> None:
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token(
        {"sub": "42"},
        expires_delta=timedelta(minutes=5),
    )
    claims = decode_access_token(token)

    assert claims["sub"] == "42"
    assert claims["exp"]

    def assert_rejected(candidate: str) -> None:
        try:
            decoded = decode_access_token(candidate)
        except (InvalidTokenError, ValueError):
            return
        assert decoded is None

    assert_rejected(f"{token}tampered")

    expired = create_access_token(
        {"sub": "42"},
        expires_delta=timedelta(seconds=-1),
    )
    assert_rejected(expired)


def test_successful_registration_sets_the_fixed_secure_cookie(
    client,
    register_user,
) -> None:
    response = register_user(client)

    assert response.status_code == 201, response.text
    assert response.request.url.scheme == "https"
    cookie_value = _assert_session_cookie(response)
    assert client.cookies.get(COOKIE_NAME) == cookie_value


def test_secure_cookie_is_not_sent_by_an_http_client(app, unique_email) -> None:
    email = unique_email("http-cookie")
    with TestClient(
        app,
        base_url="http://testserver",
        raise_server_exceptions=False,
    ) as http_client:
        registration = http_client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "correct-horse-battery-staple",
                "display_name": "HTTP Cookie User",
            },
        )

        assert registration.status_code == 201, registration.text
        _assert_session_cookie(registration)
        assert http_client.get("/api/auth/me").status_code == 401
