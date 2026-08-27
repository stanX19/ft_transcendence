"""Per-user assistant rate-limit contracts."""

from __future__ import annotations


def test_rate_limiter_is_per_user_and_expires_fixed_window() -> None:
    from app.features.ai.rate_limit import AIRateLimiter

    limiter = AIRateLimiter(clock=lambda: 0.0)

    assert limiter.allow(1, 1, now=0.0)
    assert not limiter.allow(1, 1, now=30.0)
    assert limiter.allow(2, 1, now=30.0)
    assert limiter.allow(1, 1, now=60.1)


def test_stream_route_rejects_excess_requests_for_one_user(
    client,
    register_user,
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.ai.rate_limit import ai_rate_limiter

    register = register_user(client)
    assert register.status_code == 201, register.text
    monkeypatch.setattr(get_settings(), "ai_rate_limit_per_minute", 1)
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    ai_rate_limiter.reset()

    first = client.post("/api/ai/chat/stream", json={"message": "Hello"})
    second = client.post("/api/ai/chat/stream", json={"message": "Again"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    ai_rate_limiter.reset()
