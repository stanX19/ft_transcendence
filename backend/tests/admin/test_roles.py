"""Admin role management contracts."""

from __future__ import annotations


def test_admin_can_change_role_and_librarian_cannot(
    admin_client,
    client_factory,
    register_user,
    db_session,
) -> None:
    admin, _ = admin_client()
    target = client_factory()
    target_registration = register_user(target, display_name="Role Target")
    target_id = target_registration.json()["user"]["id"]

    changed = admin.patch(f"/api/admin/users/{target_id}/role", json={"role": "LIBRARIAN"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["user"]["role"] == "LIBRARIAN"

    assert target.patch(f"/api/admin/users/{target_id}/role", json={"role": "MEMBER"}).status_code == 403
