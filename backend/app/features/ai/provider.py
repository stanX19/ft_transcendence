"""Gemini provider boundary used by the assistant services.

The rest of the application depends on this small interface instead of the
Google SDK. That keeps retrieval tests local and makes provider failures safe
to exercise with a fake provider.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import logging
from typing import Any, Protocol

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Safe, user-facing category for an upstream assistant failure."""


class AIConfigurationError(AIProviderError):
    """Raised when Gemini is not configured for this deployment."""


@dataclass(frozen=True)
class ProviderToolCall:
    """Provider-neutral function call emitted by Gemini."""

    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolAwareResponse:
    """A final provider answer plus safe tool activity for the UI."""

    text: str
    tool_events: list[dict[str, object]]


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

    @staticmethod
    def _tool_config(
        definitions: Sequence[Mapping[str, object]],
        system_instruction: str | None,
    ) -> types.GenerateContentConfig:
        declarations = [
            types.FunctionDeclaration(
                name=str(definition["name"]),
                description=str(definition.get("description", "")),
                parameters_json_schema=definition.get("parameters", {}),
            )
            for definition in definitions
        ]
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=declarations)],
        )

    @staticmethod
    def _tool_calls(response: Any) -> list[ProviderToolCall]:
        calls: list[ProviderToolCall] = []
        for call in getattr(response, "function_calls", None) or []:
            name = getattr(call, "name", None)
            if not name:
                continue
            arguments = getattr(call, "args", None) or {}
            calls.append(
                ProviderToolCall(
                    name=str(name),
                    arguments=dict(arguments),
                )
            )
        return calls

    def generate_with_tools(
        self,
        prompt: str,
        *,
        tool_definitions: Sequence[Mapping[str, object]],
        tool_executor: Callable[[str, dict[str, object]], object],
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
        max_rounds: int = 3,
    ) -> ToolAwareResponse:
        """Run bounded Gemini function calling through a supplied safe executor."""

        client = self._client_or_raise()
        config = self._tool_config(tool_definitions, system_instruction)
        contents: object = _joined_prompt(
            prompt=prompt,
            system_instruction=None,
            history=history,
        )
        events: list[dict[str, object]] = []
        try:
            for _ in range(max(1, min(int(max_rounds), 5))):
                response = client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
                calls = self._tool_calls(response)
                if not calls:
                    text = self._response_text(response)
                    if not text:
                        raise AIProviderError(
                            "The Gemini provider returned an empty response."
                        )
                    return ToolAwareResponse(text=text, tool_events=events)

                response_content = None
                candidates = getattr(response, "candidates", None) or []
                if candidates:
                    response_content = getattr(candidates[0], "content", None)
                response_parts = []
                if response_content is not None:
                    response_parts.append(response_content)
                function_parts = []
                for call in calls:
                    event: dict[str, object] = {
                        "name": call.name,
                        "status": "completed",
                    }
                    try:
                        result = tool_executor(call.name, call.arguments)
                        function_parts.append(
                            types.Part.from_function_response(
                                name=call.name,
                                response={"result": result},
                            )
                        )
                    except Exception:
                        # Tool details are application data; do not reflect them
                        # into a provider error or log message.
                        event["status"] = "error"
                        function_parts.append(
                            types.Part.from_function_response(
                                name=call.name,
                                response={"error": "Tool request was denied."},
                            )
                        )
                    events.append(event)
                response_parts.append(types.Content(role="user", parts=function_parts))
                contents = response_parts
        except AIProviderError:
            raise
        except Exception as exc:
            logger.error("Gemini tool orchestration failed: %s", type(exc).__name__)
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None

        raise AIProviderError("The Gemini provider did not finish the request.")


# The short alias makes dependency injection pleasant in route/service tests.
GeminiChatProvider = GeminiProvider
