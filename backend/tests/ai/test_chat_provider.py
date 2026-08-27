"""Gemini provider boundary and failure translation contracts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class _FakeModels:
    def __init__(self, response: object | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model: str, contents: str) -> object:
        self.calls.append({"model": model, "contents": contents})
        if self.error is not None:
            raise self.error
        return self.response


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
