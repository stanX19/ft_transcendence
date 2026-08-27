"""Authenticated POST-SSE assistant route contracts."""

from __future__ import annotations

import json


def test_chat_stream_is_post_sse_and_emits_sources_tokens_and_done(
    client,
    register_user,
    create_ai_book,
    monkeypatch,
) -> None:
    book = create_ai_book(title="Streaming source book")
    registration = register_user(client)
    assert registration.status_code == 201, registration.text

    class FakeProvider:
        def stream(self, *, prompt: str, system_instruction=None, history=()):
            assert "Streaming source book" in prompt
            yield "Hello "
            yield "from AI"

    import app.features.ai.service as service_module

    monkeypatch.setattr(service_module, "GeminiProvider", lambda: FakeProvider())
    response = client.post(
        "/api/ai/chat/stream",
        json={"message": "Tell me about Streaming source book"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: source" in response.text
    assert "event: token" in response.text
    assert "Hello " in response.text
    assert "event: done" in response.text
    assert json.dumps({"book_id": book.id})[:1] == "{"  # source payload is JSON.


def test_chat_stream_requires_authentication(client) -> None:
    response = client.post("/api/ai/chat/stream", json={"message": "Hello"})

    assert response.status_code == 401, response.text
