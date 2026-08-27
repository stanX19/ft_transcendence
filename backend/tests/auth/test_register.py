"""Registration endpoint contracts visible to a browser user."""

from __future__ import annotations

import pytest


def _user_payload(response) -> dict:
    payload = response.json()
    return payload.get("user", payload)


def test_register_normalizes_identity_trims_profile_and_starts_a_member_session(
    client,
    unique_email,
) -> None:
    raw_email = f"  {unique_email('register').upper()}  "
    response = client.post(
        "/api/auth/register",
        json={
            "email": raw_email,
            "password": "correct-horse-battery-staple",
            "display_name": "  Ada Reader  ",
        },
    )

    assert response.status_code == 201, response.text
    user = _user_payload(response)
    assert user["email"] == raw_email.strip().lower()
    assert user["display_name"] == "Ada Reader"
    assert user["role"] in ("MEMBER", "member")
    assert user["id"]
    assert "password" not in user
    assert "password_hash" not in user

    me = client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    assert _user_payload(me)["id"] == user["id"]


def test_register_rejects_duplicate_email_after_normalization(
    client,
    unique_email,
) -> None:
    email = unique_email("duplicate-register")
    first = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "First Reader",
        },
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        "/api/auth/register",
        json={
            "email": f"  {email.upper()} ",
            "password": "another-correct-password",
            "display_name": "Second Reader",
        },
    )

    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "conflict"
    assert "password" not in duplicate.text.lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("password", "short"),
        ("display_name", "A"),
        ("display_name", "A" * 81),
    ],
)
def test_register_validates_email_password_and_display_name(
    client,
    unique_email,
    field: str,
    value: str,
) -> None:
    payload = {
        "email": unique_email("invalid-register"),
        "password": "correct-horse-battery-staple",
        "display_name": "Valid Reader",
    }
    payload[field] = value

    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_register_cannot_escalate_role_through_untrusted_input(
    client,
    unique_email,
) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": unique_email("role-input"),
            "password": "correct-horse-battery-staple",
            "display_name": "Untrusted Reader",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201, response.text
    assert _user_payload(response)["role"] in ("MEMBER", "member")
