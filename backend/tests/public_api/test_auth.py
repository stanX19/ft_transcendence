"""Public API authentication and browser-session separation contracts."""

from __future__ import annotations


def test_public_namespace_rejects_missing_and_bad_keys(client, create_book) -> None:
    book = create_book(title="Public API Auth Marker")

    missing = client.get(f"/public-api/v1/books/{book.id}")
    assert missing.status_code == 401, missing.text
    assert missing.json()["error"]["code"] == "unauthenticated"

    bad = client.get(
        f"/public-api/v1/books/{book.id}",
        headers={"X-API-Key": "definitely-not-the-configured-key"},
    )
    assert bad.status_code == 401, bad.text
    assert bad.json()["error"]["code"] == "unauthenticated"


def test_valid_public_key_works_without_browser_auth(
    client,
    create_book,
    public_headers,
) -> None:
    book = create_book(title="Unauthenticated Public API Marker")

    response = client.get(
        f"/public-api/v1/books/{book.id}",
        headers=public_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["book"]["id"] == book.id
    assert not client.cookies.get("libraryos_session")


def test_browser_session_alone_does_not_authorize_public_namespace(
    client,
    register_user,
    create_book,
) -> None:
    registration = register_user(client, display_name="Internal Session User")
    assert registration.status_code == 201, registration.text
    book = create_book(title="Browser Session Separation Marker")

    response = client.get(f"/public-api/v1/books/{book.id}")

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthenticated"
