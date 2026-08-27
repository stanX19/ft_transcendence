"""Deterministic process-local public API throttling contracts."""

from __future__ import annotations


def test_configured_public_api_rate_limit_returns_429(
    client,
    create_book,
    public_headers,
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.public_api.security import public_api_rate_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "public_api_rate_limit_per_minute", 2)
    public_api_rate_limiter.reset()
    book = create_book(title="Rate Limit Marker")

    try:
        first = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
        second = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
        third = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
    finally:
        public_api_rate_limiter.reset()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert third.status_code == 429, third.text
    assert third.json()["error"]["code"] == "rate_limited"


def test_invalid_key_does_not_consume_public_api_quota(
    client,
    create_book,
    public_headers,
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.public_api.security import public_api_rate_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "public_api_rate_limit_per_minute", 1)
    public_api_rate_limiter.reset()
    book = create_book(title="Invalid Key Quota Marker")

    try:
        invalid = client.get(
            f"/public-api/v1/books/{book.id}",
            headers={"X-API-Key": "wrong"},
        )
        valid = client.get(f"/public-api/v1/books/{book.id}", headers=public_headers)
    finally:
        public_api_rate_limiter.reset()

    assert invalid.status_code == 401, invalid.text
    assert valid.status_code == 200, valid.text
