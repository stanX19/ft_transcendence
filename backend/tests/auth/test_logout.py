"""Logout invalidation and cookie-deletion contracts."""

from __future__ import annotations


def test_logout_deletes_session_cookie_and_invalidates_follow_up_requests(
    client,
    register_user,
) -> None:
    registration = register_user(client, display_name="Logout Reader")
    assert registration.status_code == 201, registration.text
    assert client.get("/api/auth/me").status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code in (200, 204), response.text
    deletion_headers = [
        header.lower()
        for header in response.headers.get_list("set-cookie")
        if header.lower().startswith("libraryos_session=")
    ]
    assert deletion_headers, response.headers
    assert any(
        "max-age=0" in header or "expires=" in header
        for header in deletion_headers
    )
    assert client.get("/api/auth/me").status_code == 401


def test_logout_does_not_return_private_session_data(
    client,
    register_user,
) -> None:
    registration = register_user(client, display_name="Logout Payload Reader")
    assert registration.status_code == 201, registration.text

    response = client.post("/api/auth/logout")

    assert "password_hash" not in response.text.lower()
    assert "access_token" not in response.text.lower()
