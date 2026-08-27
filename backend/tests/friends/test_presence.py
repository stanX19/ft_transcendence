"""Friend online status derives from last-seen timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select


def test_friend_list_reports_stale_friend_as_offline(
    client_factory,
    register_user,
    db_session,
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.users.models import User

    owner = client_factory()
    owner_registration = register_user(owner, display_name="Presence Owner")
    target = client_factory()
    target_registration = register_user(target, display_name="Presence Target")
    target_id = target_registration.json()["user"]["id"]
    target_user = db_session.scalar(select(User).where(User.id == target_id))
    assert target_user is not None
    target_user.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=90)
    db_session.commit()

    monkeypatch.setenv("ONLINE_THRESHOLD_SECONDS", "60")
    get_settings.cache_clear()
    assert owner.post(f"/api/friends/{target_id}").status_code == 201
    items = owner.get("/api/friends").json()["items"]
    friend = next(item for item in items if item["id"] == target_id)
    assert friend["is_online"] is False
