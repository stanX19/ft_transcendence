"""Gemini provider boundary and failure translation contracts."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest


class _FakeModels:
    def __init__(
        self,
        response: object | None = None,
        error: Exception | None = None,
        stream_chunks: list[object] | None = None,
        stream_error: Exception | None = None,
    ):
        self.response = response
        self.error = error
        self.stream_chunks = stream_chunks or []
        self.stream_error = stream_error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model: str, contents: str) -> object:
        self.calls.append({"model": model, "contents": contents})
        if self.error is not None:
            raise self.error
        return self.response

    def generate_content_stream(self, *, model: str, contents: str):
        self.calls.append({"model": model, "contents": contents})
        if self.stream_error is not None:
            raise self.stream_error
        return iter(self.stream_chunks)


class _FakeClient:
    def __init__(self, models: _FakeModels):
        self.models = models


def test_provider_uses_injected_fake_gemini_client_without_network() -> None:
    from app.features.ai.provider import GeminiProvider

    models = _FakeModels(response=SimpleNamespace(text="A fake grounded answer."))
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="fake-key",
            gemini_model="fake-model",
        ),
        client=_FakeClient(models),
    )

    answer = provider.generate(prompt="Use the supplied catalog context.")

    assert answer == "A fake grounded answer."
    assert len(models.calls) == 1
    assert models.calls[0]["model"] == "fake-model"
    assert "Use the supplied catalog context." in models.calls[0]["contents"]


def test_provider_translates_missing_key_to_safe_configuration_error() -> None:
    from app.features.ai.provider import (
        AIConfigurationError,
        GeminiProvider,
    )

    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_model="fake-model",
        ),
        client=None,
    )

    with pytest.raises(AIConfigurationError) as raised:
        provider.generate(prompt="This must not call Gemini.")

    assert "configured" in str(raised.value).lower()


def test_provider_translates_sdk_failure_to_safe_provider_error() -> None:
    from app.features.ai.provider import (
        AIProviderError,
        GeminiProvider,
    )

    models = _FakeModels(error=RuntimeError("private SDK/network detail"))
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="fake-key",
            gemini_model="fake-model",
        ),
        client=_FakeClient(models),
    )

    with pytest.raises(AIProviderError) as raised:
        provider.generate(prompt="A prompt")

    assert "private sdk/network detail" not in str(raised.value).lower()
    assert str(raised.value).strip()


def test_provider_rotates_to_next_key_after_a_rate_limit(monkeypatch) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import GeminiProvider

    class RateLimitedError(Exception):
        code = 429

    clients: dict[str, _FakeModels] = {}

    def client_factory(*, api_key: str):
        models = _FakeModels(
            response=SimpleNamespace(text="Answer from key two.")
            if api_key == "key-two"
            else None,
            error=RateLimitedError("quota detail") if api_key == "key-one" else None,
        )
        clients[api_key] = models
        return _FakeClient(models)

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two", "key-three"],
            gemini_model="fake-model",
        )
    )

    answer = provider.generate(prompt="A catalog question")

    assert answer == "Answer from key two."
    assert list(clients) == ["key-one", "key-two"]
    assert len(clients["key-one"].calls) == 1
    assert len(clients["key-two"].calls) == 1


def test_provider_retries_three_times_then_wraps_back_to_first_key(
    monkeypatch,
    caplog,
) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import AIProviderError, GeminiProvider

    class RateLimitedError(Exception):
        code = 429

    calls: list[str] = []

    def client_factory(*, api_key: str):
        class Models:
            def generate_content(self, *, model: str, contents: str):
                del model, contents
                calls.append(api_key)
                raise RateLimitedError("private quota detail")

        return _FakeClient(Models())

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two", "key-three"],
            gemini_model="fake-model",
        )
    )

    with caplog.at_level(logging.INFO, logger="app.features.ai.provider"):
        with pytest.raises(AIProviderError):
            provider.generate(prompt="A catalog question")

    assert calls == ["key-one", "key-two", "key-three", "key-one"]
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "app.features.ai.provider"
    ]
    assert any(event["event"] == "gemini_key_rotated" for event in events)
    assert any(
        event["event"] == "gemini_request_exhausted" for event in events
    )
    safe_log = " ".join(record.getMessage() for record in caplog.records)
    assert "key-one" not in safe_log
    assert "key-two" not in safe_log
    assert "key-three" not in safe_log
    assert "private quota detail" not in safe_log


def test_provider_rotates_streaming_requests_after_a_rate_limit(monkeypatch) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import GeminiProvider

    class RateLimitedError(Exception):
        code = 429

    clients: dict[str, _FakeModels] = {}

    def client_factory(*, api_key: str):
        models = _FakeModels(
            stream_chunks=[
                SimpleNamespace(text="Grounded "),
                SimpleNamespace(text="stream."),
            ]
            if api_key == "key-two"
            else [],
            stream_error=RateLimitedError("quota detail")
            if api_key == "key-one"
            else None,
        )
        clients[api_key] = models
        return _FakeClient(models)

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two"],
            gemini_model="fake-model",
        )
    )

    chunks = list(provider.stream(prompt="A catalog question"))

    assert chunks == ["Grounded ", "stream."]
    assert len(clients["key-one"].calls) == 1
    assert len(clients["key-two"].calls) == 1


def test_provider_uses_legacy_key_when_the_configured_list_has_no_usable_keys(
    monkeypatch,
) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import GeminiProvider

    used_keys: list[str] = []

    def client_factory(*, api_key: str):
        used_keys.append(api_key)
        return _FakeClient(
            _FakeModels(response=SimpleNamespace(text="Legacy answer."))
        )

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="legacy-key",
            gemini_api_key_list=["", "  "],
            gemini_model="fake-model",
        )
    )

    assert provider.generate(prompt="A catalog question") == "Legacy answer."
    assert used_keys == ["legacy-key"]


def test_provider_does_not_rotate_non_rate_limit_failures(monkeypatch) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import AIProviderError, GeminiProvider

    class ServiceUnavailableError(Exception):
        code = 503

    used_keys: list[str] = []

    def client_factory(*, api_key: str):
        used_keys.append(api_key)
        return _FakeClient(_FakeModels(error=ServiceUnavailableError()))

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two"],
            gemini_model="fake-model",
        )
    )

    with pytest.raises(AIProviderError):
        provider.generate(prompt="A catalog question")

    assert used_keys == ["key-one"]


def test_provider_does_not_retry_a_stream_after_partial_output(monkeypatch) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import AIProviderError, GeminiProvider

    class RateLimitedError(Exception):
        code = 429

    used_keys: list[str] = []

    def client_factory(*, api_key: str):
        class Models:
            def generate_content_stream(self, *, model: str, contents: str):
                del model, contents
                used_keys.append(api_key)
                yield SimpleNamespace(text="Partial answer ")
                raise RateLimitedError()

        return _FakeClient(Models())

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two"],
            gemini_model="fake-model",
        )
    )

    with pytest.raises(AIProviderError):
        list(provider.stream(prompt="A catalog question"))

    assert used_keys == ["key-one"]


def test_provider_applies_rotation_to_tool_requests(monkeypatch) -> None:
    from app.features.ai import provider as provider_module
    from app.features.ai.provider import GeminiProvider

    class RateLimitedError(Exception):
        code = 429

    used_keys: list[str] = []

    def client_factory(*, api_key: str):
        class Models:
            def generate_content(self, *, model: str, contents: object, config: object):
                del model, contents, config
                used_keys.append(api_key)
                if api_key == "key-one":
                    raise RateLimitedError()
                return SimpleNamespace(text="Tool-grounded answer.")

        return _FakeClient(Models())

    monkeypatch.setattr(provider_module.genai, "Client", client_factory)
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="",
            gemini_api_key_list=["key-one", "key-two"],
            gemini_model="fake-model",
        )
    )

    result = provider.generate_with_tools(
        "A catalog question",
        tool_definitions=[
            {
                "name": "search_catalog",
                "description": "Search the catalog.",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        tool_executor=lambda name, arguments: {"name": name, "arguments": arguments},
    )

    assert result.text == "Tool-grounded answer."
    assert used_keys == ["key-one", "key-two"]


def test_provider_preserves_tool_call_context_for_the_follow_up_request() -> None:
    from app.features.ai.provider import GeminiProvider

    function_call = SimpleNamespace(
        name="navigate_to_page",
        args={"destination": "book", "book_id": 14},
    )
    model_content = SimpleNamespace(role="model")

    class Models:
        def __init__(self) -> None:
            self.contents: list[object] = []
            self.responses = [
                SimpleNamespace(
                    function_calls=[function_call],
                    candidates=[SimpleNamespace(content=model_content)],
                ),
                SimpleNamespace(text="Opening the book page."),
            ]

        def generate_content(self, *, model: str, contents: object, config: object):
            del model, config
            self.contents.append(contents)
            return self.responses.pop(0)

    models = Models()
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="fake-key",
            gemini_model="fake-model",
        ),
        client=_FakeClient(models),
    )

    result = provider.generate_with_tools(
        "Take me to book 14.",
        tool_definitions=[
            {
                "name": "navigate_to_page",
                "description": "Open a safe internal page.",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        tool_executor=lambda name, arguments: {
            "action": "navigate",
            "destination": arguments["destination"],
            "path": "/books/14",
            "book_id": 14,
        },
    )

    assert result.text == "Opening the book page."
    assert len(models.contents) == 2
    follow_up = models.contents[1]
    assert isinstance(follow_up, list)
    assert follow_up[0].role == "user"
    assert follow_up[1] is model_content
    assert follow_up[2].role == "user"


def test_provider_accepts_only_canonical_navigation_actions() -> None:
    from app.features.ai.provider import GeminiProvider

    canonical = {
        "action": "navigate",
        "destination": "book",
        "path": "/books/14",
        "book_id": 14,
    }

    assert GeminiProvider._safe_navigation_action(canonical) == canonical
    assert GeminiProvider._safe_navigation_action({
        **canonical,
        "path": "https://example.com",
    }) is None
    assert GeminiProvider._safe_navigation_action({
        **canonical,
        "path": "/books/15",
    }) is None
    assert GeminiProvider._safe_navigation_action({
        **canonical,
        "destination": "unknown",
        "path": "/unknown",
    }) is None


def test_provider_streams_text_after_a_tool_round() -> None:
    from app.features.ai.provider import GeminiProvider

    function_call = SimpleNamespace(
        name="navigate_to_page",
        args={"destination": "book", "book_id": 14},
    )
    model_content = SimpleNamespace(role="model")

    class Models:
        def __init__(self) -> None:
            self.calls = 0

        def generate_content_stream(self, *, model: str, contents: object, config: object):
            del model, contents, config
            self.calls += 1
            if self.calls == 1:
                return iter([
                    SimpleNamespace(
                        function_calls=[function_call],
                        candidates=[SimpleNamespace(content=model_content)],
                    )
                ])
            return iter([
                SimpleNamespace(text="Opening "),
                SimpleNamespace(text="the book page."),
            ])

    models = Models()
    provider = GeminiProvider(
        settings=SimpleNamespace(
            gemini_api_key="fake-key",
            gemini_model="fake-model",
        ),
        client=_FakeClient(models),
    )

    events = list(provider.stream_with_tools(
        "Take me to book 14.",
        tool_definitions=[
            {
                "name": "navigate_to_page",
                "description": "Open a safe internal page.",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        tool_executor=lambda name, arguments: {
            "action": "navigate",
            "destination": arguments["destination"],
            "path": "/books/14",
            "book_id": 14,
        },
    ))

    assert events[0][0] == "tool"
    assert events[0][1]["action"]["path"] == "/books/14"
    assert [event[1]["text"] for event in events[1:]] == [
        "Opening ",
        "the book page.",
    ]


def test_settings_parses_the_json_key_list(monkeypatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("GEMINI_API_KEY_LIST", '["one", "two"]')

    settings = Settings(_env_file=None)

    assert settings.gemini_api_key_list == ["one", "two"]


def test_telemetry_allowlist_drops_prompt_and_nested_payloads(caplog) -> None:
    from app.features.ai.telemetry import log_event

    logger = logging.getLogger("app.features.ai.telemetry-test")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            logging.INFO,
            "telemetry_contract",
            source_count=2,
            prompt="private prompt marker",
            payload={"private": "account data"},
        )

    event = json.loads(caplog.records[-1].getMessage())
    assert event["source_count"] == 2
    assert "prompt" not in event
    assert "payload" not in event
    assert "private prompt marker" not in caplog.records[-1].getMessage()
