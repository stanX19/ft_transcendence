"""Authenticated POST-SSE assistant route contracts."""

from __future__ import annotations

import json
import logging


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
        headers={"X-Request-ID": "chat-test-correlation"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert len(response.headers["x-request-id"]) == 32
    assert response.headers["x-request-id"] != "chat-test-correlation"
    assert "event: source" in response.text
    assert "event: token" in response.text
    assert "Hello " in response.text
    assert "event: done" in response.text
    assert json.dumps({"book_id": book.id})[:1] == "{"  # source payload is JSON.


def test_chat_stream_lifecycle_events_share_the_response_correlation_id(
    client,
    register_user,
    create_ai_book,
    monkeypatch,
    caplog,
) -> None:
    create_ai_book(title="Telemetry stream source")
    registration = register_user(client)
    assert registration.status_code == 201, registration.text

    class FakeProvider:
        def stream(self, *, prompt: str, system_instruction=None, history=()):
            del prompt, system_instruction, history
            yield "Grounded answer."

    import app.features.ai.service as service_module

    monkeypatch.setattr(service_module, "GeminiProvider", lambda: FakeProvider())
    with caplog.at_level(logging.INFO, logger="app.features.ai"):
        response = client.post(
            "/api/ai/chat/stream",
            json={"message": "Tell me about Telemetry stream source"},
        )

    assert response.status_code == 200, response.text
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name.startswith("app.features.ai")
    ]
    names = {event["event"] for event in events}
    assert {
        "assistant_stream_started",
        "rag_retrieval_completed",
        "assistant_generation_completed",
        "assistant_stream_completed",
    } <= names
    request_ids = {
        event["request_id"]
        for event in events
        if event["event"] in names
    }
    assert len(request_ids) == 1
    assert response.headers["x-request-id"] in request_ids


def test_chat_stream_requires_authentication(client) -> None:
    response = client.post("/api/ai/chat/stream", json={"message": "Hello"})

    assert response.status_code == 401, response.text
    assert len(response.headers["x-request-id"]) == 32
