"""Safe assistant failure contracts."""

from __future__ import annotations


def test_missing_gemini_configuration_is_an_sse_error_not_an_api_crash(
    client,
    register_user,
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.ai.rate_limit import ai_rate_limiter

    register = register_user(client)
    assert register.status_code == 201, register.text
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    monkeypatch.setattr(get_settings(), "gemini_api_key_list", [])
    ai_rate_limiter.reset()

    response = client.post("/api/ai/chat/stream", json={"message": "Hello"})

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "Traceback" not in response.text
    assert "libraryos_session" not in response.text
    assert "api key" in response.text.lower()
    ai_rate_limiter.reset()
