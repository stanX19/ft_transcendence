"""Configurable last-seen activity and online-status contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select


def _user_payload(response) -> dict:
    payload = response.json()
    return payload.get("user", payload)


def _find_user(db_session, email: str):
    from app.features.users.models import User

    return db_session.scalar(select(User).where(User.email == email))


def test_authenticated_activity_updates_last_seen_at(
    client,
    register_user,
    db_session,
) -> None:
    registration = register_user(client, display_name="Presence Activity Reader")
    assert registration.status_code == 201, registration.text
    email = _user_payload(registration)["email"]

    user = _find_user(db_session, email)
    assert user is not None
    old_seen = datetime.now(timezone.utc) - timedelta(minutes=10)
    user.last_seen_at = old_seen
    db_session.commit()

    response = client.get("/api/auth/me")

    assert response.status_code == 200, response.text
    db_session.expire_all()
    refreshed = _find_user(db_session, email)
    assert refreshed is not None
    assert refreshed.last_seen_at is not None
    assert refreshed.last_seen_at > old_seen


def test_online_status_uses_the_configurable_threshold(
    client_factory,
    register_user,
    db_session,
    monkeypatch,
) -> None:
    target_client = client_factory()
    registration = register_user(
        target_client,
        display_name="Threshold Presence Target",
    )
    assert registration.status_code == 201, registration.text
    target = _user_payload(registration)

    user = _find_user(db_session, target["email"])
    assert user is not None
    user.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=90)
    db_session.commit()

    public_client = client_factory()
    try:
        monkeypatch.setenv("ONLINE_THRESHOLD_SECONDS", "60")
        from app.core.config import get_settings

        get_settings.cache_clear()
        offline = public_client.get(f"/api/users/{target['id']}")
        assert offline.status_code == 200, offline.text
        assert _user_payload(offline)["is_online"] is False

        monkeypatch.setenv("ONLINE_THRESHOLD_SECONDS", "120")
        get_settings.cache_clear()
        online = public_client.get(f"/api/users/{target['id']}")
        assert online.status_code == 200, online.text
        assert _user_payload(online)["is_online"] is True
    finally:
        get_settings.cache_clear()
