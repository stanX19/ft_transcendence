"""Gemini provider boundary used by the assistant services.

The rest of the application depends on this small interface instead of the
Google SDK. That keeps retrieval tests local and makes provider failures safe
to exercise with a fake provider.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
import logging
from typing import Any, Protocol

from google import genai

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Safe, user-facing category for an upstream assistant failure."""


class AIConfigurationError(AIProviderError):
    """Raised when Gemini is not configured for this deployment."""


class ChatProvider(Protocol):
    """Minimal provider contract that test fakes can implement."""

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
    ) -> str:
        """Generate one complete answer."""

    def stream(
        self,
        *,
        prompt: str,
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
    ) -> Iterable[str]:
        """Yield answer text chunks."""


def _joined_prompt(
    *,
    prompt: str,
    system_instruction: str | None,
    history: Sequence[dict[str, str]],
) -> str:
    """Build provider-neutral contents while preserving recent chat context."""

    if not system_instruction and not history:
        return prompt.strip()

    sections: list[str] = []
    if system_instruction:
        sections.append(f"System instructions:\n{system_instruction.strip()}")
    for message in history:
        role = str(message.get("role", "user")).strip().lower() or "user"
        text = str(message.get("text", "")).strip()
        if text:
            sections.append(f"{role.title()}:\n{text}")
    sections.append(f"User:\n{prompt.strip()}")
    return "\n\n".join(sections)


class GeminiProvider:
    """Thin synchronous adapter around ``google-genai``."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._api_key = (
            self.settings.gemini_api_key if api_key is None else api_key
        )
        self._client = client
        self._model = model or self.settings.gemini_model or "gemini-2.0-flash"

    def _client_or_raise(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key.strip():
            raise AIConfigurationError(
                "The AI assistant is not configured: a Gemini API key is required."
            )
        try:
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:  # SDK/configuration details must stay private.
            logger.error("Gemini client initialization failed: %s", type(exc).__name__)
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None
        return self._client

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text.strip()
        return ""

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
    ) -> str:
        """Generate a complete response and normalize empty SDK output."""

        contents = _joined_prompt(
            prompt=prompt,
            system_instruction=system_instruction,
            history=history,
        )
        try:
            response = self._client_or_raise().models.generate_content(
                model=self._model,
                contents=contents,
            )
        except AIProviderError:
            raise
        except Exception as exc:  # Do not reflect SDK messages or credentials.
            logger.error("Gemini generation failed: %s", type(exc).__name__)
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None

        answer = self._response_text(response)
        if not answer:
            raise AIProviderError("The AI assistant returned an empty response.")
        return answer

    def stream(
        self,
        *,
        prompt: str,
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
    ) -> Iterator[str]:
        """Yield non-empty text chunks from Gemini's streaming API."""

        contents = _joined_prompt(
            prompt=prompt,
            system_instruction=system_instruction,
            history=history,
        )
        try:
            chunks = self._client_or_raise().models.generate_content_stream(
                model=self._model,
                contents=contents,
            )
            for chunk in chunks:
                text = self._response_text(chunk)
                if text:
                    yield text
        except AIProviderError:
            raise
        except Exception as exc:  # Do not reflect SDK messages or credentials.
            logger.error("Gemini streaming failed: %s", type(exc).__name__)
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None


# The short alias makes dependency injection pleasant in route/service tests.
GeminiChatProvider = GeminiProvider
