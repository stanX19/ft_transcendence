"""Cross-cutting privilege boundaries remain enforced by the backend."""

from __future__ import annotations


def test_librarian_cannot_call_admin_user_operations(client, register_user) -> None:
    registration = register_user(client, display_name="Catalog Librarian")
    assert registration.status_code == 201, registration.text
    assert client.get("/api/admin/users").status_code == 403
