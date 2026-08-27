"""Shared admin API fixtures."""

from __future__ import annotations

from collections.abc import Callable
from sqlalchemy import select
import pytest


@pytest.fixture
def admin_client(client_factory, register_user, db_session) -> Callable[[], tuple[object, dict]]:
    def make_admin():
        from app.features.users.models import User, UserRole

        client = client_factory()
        registration = register_user(client, display_name="System Admin")
        assert registration.status_code == 201, registration.text
        user_id = registration.json()["user"]["id"]
        user = db_session.scalar(select(User).where(User.id == user_id))
        assert user is not None
        user.role = UserRole.ADMIN
        db_session.commit()
        return client, registration.json()["user"]

    return make_admin
