"""Current-user endpoint and authentication-boundary contracts."""

from __future__ import annotations


def _user_payload(response) -> dict:
    payload = response.json()
    return payload.get("user", payload)


def test_me_rejects_requests_without_a_session(client) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_me_returns_authenticated_user_without_private_password_data(
    client,
    register_user,
) -> None:
    registration = register_user(client, display_name="Current Reader")
    assert registration.status_code == 201, registration.text

    response = client.get("/api/auth/me")

    assert response.status_code == 200, response.text
    user = _user_payload(response)
    assert user["email"]
    assert user["display_name"] == "Current Reader"
    assert user["role"] in ("MEMBER", "member")
    assert "password" not in user
    assert "password_hash" not in user


def test_me_rejects_a_tampered_session_cookie_without_leaking_details(client) -> None:
    client.cookies.set(
        "libraryos_session",
        "not-a-valid-signed-jwt",
        domain="testserver",
        path="/",
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert "traceback" not in response.text.lower()
    assert "not-a-valid-signed-jwt" not in response.text
