"""Profile, privacy, and authenticated-directory API contracts."""

from __future__ import annotations


PRIVATE_USER_KEYS = {
    "password",
    "password_hash",
    "last_seen_at",
    "created_at",
    "updated_at",
}


def _user_payload(response) -> dict:
    payload = response.json()
    return payload.get("user", payload)


def _directory_items(response) -> list[dict]:
    payload = response.json()
    if isinstance(payload, list):
        return payload
    assert isinstance(payload, dict)
    assert "items" in payload
    return payload["items"]


def test_public_profile_is_readable_without_auth_and_excludes_private_fields(
    client_factory,
    register_user,
) -> None:
    owner_client = client_factory()
    registration = register_user(owner_client, display_name="Public Profile Reader")
    assert registration.status_code == 201, registration.text
    user_id = _user_payload(registration)["id"]

    anonymous_client = client_factory()
    response = anonymous_client.get(f"/api/users/{user_id}")

    assert response.status_code == 200, response.text
    profile = _user_payload(response)
    assert profile["id"] == user_id
    assert profile["display_name"] == "Public Profile Reader"
    assert "bio" in profile
    assert "is_online" in profile
    assert not PRIVATE_USER_KEYS.intersection(profile)
    assert "email" not in profile
    assert "role" not in profile


def test_authenticated_user_can_update_only_own_profile_fields(
    client,
    register_user,
) -> None:
    registration = register_user(client, display_name="Original Profile Reader")
    assert registration.status_code == 201, registration.text
    original = _user_payload(registration)

    update = client.patch(
        "/api/users/me",
        json={
            "display_name": "Updated Profile Reader",
            "bio": "A short public biography.",
        },
    )

    assert update.status_code == 200, update.text
    updated = _user_payload(update)
    assert updated["id"] == original["id"]
    assert updated["display_name"] == "Updated Profile Reader"
    assert updated["bio"] == "A short public biography."
    assert updated["email"] == original["email"]
    assert updated["role"] in ("MEMBER", "member")
    assert not PRIVATE_USER_KEYS.intersection(updated)

    attempted_escalation = client.patch(
        "/api/users/me",
        json={"email": "attacker@example.test", "role": "ADMIN"},
    )
    assert attempted_escalation.status_code in (200, 422)

    me = client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    current = _user_payload(me)
    assert current["email"] == original["email"]
    assert current["role"] in ("MEMBER", "member")


def test_profile_patch_validates_display_name_and_requires_auth(
    client_factory,
    register_user,
) -> None:
    anonymous_client = client_factory()
    unauthenticated = anonymous_client.patch(
        "/api/users/me",
        json={"display_name": "Anonymous Update"},
    )
    assert unauthenticated.status_code == 401

    registration = register_user(
        client_factory(),
        display_name="Validation Profile Reader",
    )
    assert registration.status_code == 201, registration.text
    authenticated_client = client_factory()
    # A fresh client has no cookie; log in through the endpoint under test's
    # normal browser flow before checking backend validation.
    login = authenticated_client.post(
        "/api/auth/login",
        json={
            "email": _user_payload(registration)["email"],
            "password": "correct-horse-battery-staple",
        },
    )
    assert login.status_code == 200, login.text

    for display_name in ("", "A", "B" * 81):
        response = authenticated_client.patch(
            "/api/users/me",
            json={"display_name": display_name},
        )
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "validation_error"


def test_authenticated_directory_search_returns_public_profile_stubs(
    client_factory,
    register_user,
) -> None:
    target_client = client_factory()
    target = register_user(target_client, display_name="Alice Directory Target")
    assert target.status_code == 201, target.text
    target_user = _user_payload(target)

    search_client = client_factory()
    search_user = register_user(search_client, display_name="Directory Searcher")
    assert search_user.status_code == 201, search_user.text

    response = search_client.get(
        "/api/users",
        params={"query": "alice directory", "page": 1},
    )

    assert response.status_code == 200, response.text
    items = _directory_items(response)
    match = next((item for item in items if item["id"] == target_user["id"]), None)
    assert match is not None
    assert match["display_name"] == "Alice Directory Target"
    assert "email" not in match
    assert not PRIVATE_USER_KEYS.intersection(match)
    assert "role" not in match


def test_public_profile_returns_not_found_for_unknown_user(client) -> None:
    response = client.get("/api/users/2147483647")

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"
