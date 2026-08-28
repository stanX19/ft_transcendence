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


def test_chat_stream_emits_a_safe_navigation_tool_action(
    client,
    register_user,
    create_ai_book,
    monkeypatch,
) -> None:
    book = create_ai_book(title="Navigation stream source")
    registration = register_user(client)
    assert registration.status_code == 201, registration.text

    from app.features.ai.provider import ToolAwareResponse

    class ToolProvider:
        def generate_with_tools(self, prompt, **kwargs):
            del prompt, kwargs
            return ToolAwareResponse(
                text="Opening the book page so you can borrow it.",
                tool_events=[
                    {
                        "name": "navigate_to_page",
                        "status": "completed",
                        "action": {
                            "action": "navigate",
                            "destination": "book",
                            "path": f"/books/{book.id}",
                            "book_id": book.id,
                        },
                    }
                ],
            )

    import app.features.ai.service as service_module

    monkeypatch.setattr(service_module, "GeminiProvider", lambda: ToolProvider())
    response = client.post(
        "/api/ai/chat/stream",
        json={"message": "Take me to this book so I can borrow it"},
    )

    assert response.status_code == 200, response.text
    assert "event: tool" in response.text
    assert '"path":"/books/' in response.text
    assert "event: token" in response.text
    assert "Opening the book page" in response.text


def test_chat_stream_uses_the_streaming_tool_provider_path(
    client,
    register_user,
    create_ai_book,
    monkeypatch,
) -> None:
    book = create_ai_book(title="Streaming navigation source")
    registration = register_user(client)
    assert registration.status_code == 201, registration.text

    class ToolProvider:
        def stream_with_tools(self, prompt, **kwargs):
            del prompt, kwargs
            yield (
                "tool",
                {
                    "name": "navigate_to_page",
                    "status": "completed",
                    "action": {
                        "action": "navigate",
                        "destination": "book",
                        "path": f"/books/{book.id}",
                        "book_id": book.id,
                    },
                },
            )
            yield "token", {"text": "Opening the book page."}

    import app.features.ai.service as service_module

    monkeypatch.setattr(service_module, "GeminiProvider", lambda: ToolProvider())
    response = client.post(
        "/api/ai/chat/stream",
        json={"message": f"Take me to book {book.id} so I can borrow it"},
    )

    assert response.status_code == 200, response.text
    assert '"name":"navigate_to_page","status":"completed"' in response.text
    assert f'"path":"/books/{book.id}"' in response.text
    assert "Opening the book page" in response.text
    assert "event: done" in response.text


def test_chat_stream_rejects_a_nonexistent_navigation_target(
    client,
    register_user,
    monkeypatch,
) -> None:
    registration = register_user(client)
    assert registration.status_code == 201, registration.text

    from app.features.ai.provider import ToolAwareResponse

    class ToolProvider:
        def generate_with_tools(self, prompt, **kwargs):
            del prompt, kwargs
            return ToolAwareResponse(
                text="I cannot open that book.",
                tool_events=[
                    {
                        "name": "navigate_to_page",
                        "status": "completed",
                        "action": {
                            "action": "navigate",
                            "destination": "book",
                            "path": "/books/2147483647",
                            "book_id": 2147483647,
                        },
                    }
                ],
            )

    import app.features.ai.service as service_module

    monkeypatch.setattr(service_module, "GeminiProvider", lambda: ToolProvider())
    response = client.post(
        "/api/ai/chat/stream",
        json={"message": "Take me to the missing book"},
    )

    assert response.status_code == 200, response.text
    assert '"name":"navigate_to_page","status":"error"' in response.text
    assert '"action"' not in response.text
