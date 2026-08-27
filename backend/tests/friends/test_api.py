"""Immediate add/remove/list friendship API contracts."""

from __future__ import annotations


def test_add_remove_and_list_friend_is_immediate_and_canonical(
    client_factory,
    register_user,
) -> None:
    owner = client_factory()
    owner_registration = register_user(owner, display_name="Friend Owner")
    friend = client_factory()
    friend_registration = register_user(friend, display_name="Friend Target")
    assert owner_registration.status_code == 201, owner_registration.text
    assert friend_registration.status_code == 201, friend_registration.text
    friend_id = friend_registration.json()["user"]["id"]

    added = owner.post(f"/api/friends/{friend_id}")
    assert added.status_code == 201, added.text
    duplicate = owner.post(f"/api/friends/{friend_id}")
    assert duplicate.status_code == 409, duplicate.text
    listed = owner.get("/api/friends")
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == friend_id for item in listed.json()["items"])

    removed = owner.delete(f"/api/friends/{friend_id}")
    assert removed.status_code in (200, 204), removed.text
    assert not any(item["id"] == friend_id for item in owner.get("/api/friends").json()["items"])


def test_self_friendship_and_unrelated_removal_are_rejected(client, register_user) -> None:
    registration = register_user(client, display_name="Self Friend User")
    user_id = registration.json()["user"]["id"]

    self_add = client.post(f"/api/friends/{user_id}")
    assert self_add.status_code == 409, self_add.text
    missing_remove = client.delete("/api/friends/2147483647")
    assert missing_remove.status_code == 404, missing_remove.text
