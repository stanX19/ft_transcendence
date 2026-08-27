"""Backend role values and authorization dependency contracts."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select


def _add_librarian_route(app) -> None:
    from app.core.dependencies import require_roles

    @app.get("/api/test/role-guard", include_in_schema=False)
    def role_guard_probe(current_user=Depends(require_roles("LIBRARIAN", "ADMIN"))):
        return {"user_id": current_user.id}


def test_member_is_rejected_by_a_privileged_backend_role_guard(
    client,
    register_user,
    app_with_temporary_routes,
) -> None:
    _add_librarian_route(app_with_temporary_routes)
    registration = register_user(client, display_name="Member Guard Reader")
    assert registration.status_code == 201, registration.text

    response = client.get("/api/test/role-guard")

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_privileged_role_is_allowed_and_unauthenticated_users_are_rejected(
    client_factory,
    register_user,
    login_user,
    unique_email,
    db_session,
    app_with_temporary_routes,
) -> None:
    _add_librarian_route(app_with_temporary_routes)
    email = unique_email("librarian-guard")
    setup_client = client_factory()
    registration = register_user(
        setup_client,
        email=email,
        display_name="Librarian Guard User",
    )
    assert registration.status_code == 201, registration.text

    from app.features.users.models import User

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = "LIBRARIAN"
    db_session.commit()

    librarian_client = client_factory()
    login = login_user(librarian_client, email=email)
    assert login.status_code == 200, login.text
    assert librarian_client.get("/api/test/role-guard").status_code == 200

    anonymous_client = client_factory()
    anonymous = anonymous_client.get("/api/test/role-guard")
    assert anonymous.status_code == 401, anonymous.text
