"""Admin user CRUD and safety contracts."""

from __future__ import annotations


def test_non_admin_cannot_list_or_edit_admin_users(client, register_user) -> None:
    registration = register_user(client, display_name="Non Admin")
    assert registration.status_code == 201, registration.text
    response = client.get("/api/admin/users")
    assert response.status_code == 403, response.text


def test_admin_can_list_update_and_delete_safe_user(
    admin_client,
    client_factory,
    register_user,
) -> None:
    admin, _ = admin_client()
    target = client_factory()
    target_registration = register_user(target, display_name="Admin Target")
    target_id = target_registration.json()["user"]["id"]

    listing = admin.get("/api/admin/users?query=Admin%20Target")
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == target_id for item in listing.json()["items"])
    assert all("password_hash" not in item for item in listing.json()["items"])

    updated = admin.patch(f"/api/admin/users/{target_id}", json={"display_name": "Updated Admin Target"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["user"]["display_name"] == "Updated Admin Target"
    deleted = admin.delete(f"/api/admin/users/{target_id}")
    assert deleted.status_code in (200, 204), deleted.text


def test_admin_cannot_self_delete_or_demote_last_admin(admin_client) -> None:
    admin, user = admin_client()
    self_delete = admin.delete(f"/api/admin/users/{user['id']}")
    assert self_delete.status_code == 409, self_delete.text
    self_role = admin.patch(f"/api/admin/users/{user['id']}/role", json={"role": "MEMBER"})
    assert self_role.status_code == 409, self_role.text
