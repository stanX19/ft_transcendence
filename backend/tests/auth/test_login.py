"""Login and credential-error contracts."""

from __future__ import annotations


def _user_payload(response) -> dict:
    payload = response.json()
    return payload.get("user", payload)


def _assert_login_cookie(response) -> None:
    headers = response.headers.get_list("set-cookie")
    cookie = next(
        (
            header
            for header in headers
            if header.lower().startswith("libraryos_session=")
        ),
        None,
    )
    assert cookie is not None, headers
    attributes = cookie.lower()
    assert "secure" in attributes
    assert "httponly" in attributes
    assert "samesite=lax" in attributes
    assert "path=/" in attributes


def test_login_accepts_normalized_email_and_returns_authenticated_user(
    client,
    register_user,
    login_user,
    unique_email,
) -> None:
    email = unique_email("login")
    registered = register_user(client, email=email, display_name="Login Reader")
    assert registered.status_code == 201, registered.text
    registered_user = _user_payload(registered)

    client.cookies.clear()
    response = login_user(
        client,
        email=f"  {email.upper()} ",
    )

    assert response.status_code == 200, response.text
    _assert_login_cookie(response)
    user = _user_payload(response)
    assert user["id"] == registered_user["id"]
    assert "password" not in user
    assert "password_hash" not in user
    assert client.get("/api/auth/me").status_code == 200


def test_unknown_email_and_wrong_password_have_the_same_generic_failure(
    client_factory,
    register_user,
    login_user,
    unique_email,
) -> None:
    setup_client = client_factory()
    known_email = unique_email("generic-login")
    registration = register_user(
        setup_client,
        email=known_email,
        display_name="Generic Login Reader",
    )
    assert registration.status_code == 201, registration.text

    wrong_password_client = client_factory()
    unknown_email_client = client_factory()
    wrong_password = login_user(
        wrong_password_client,
        email=known_email,
        password="wrong-password-value",
    )
    unknown_email = login_user(
        unknown_email_client,
        email=unique_email("does-not-exist"),
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert known_email not in wrong_password.text
    assert known_email not in unknown_email.text
    assert "password_hash" not in wrong_password.text.lower()
    assert "password_hash" not in unknown_email.text.lower()


def test_login_rejects_invalid_input_before_authentication(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"
