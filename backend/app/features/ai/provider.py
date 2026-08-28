"""Gemini provider boundary used by the assistant services.

The rest of the application depends on this small interface instead of the
Google SDK. That keeps retrieval tests local and makes provider failures safe
to exercise with a fake provider.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
from threading import Lock
from typing import Any, Protocol

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings
from app.features.ai.telemetry import log_event
from app.features.ai.tools import canonical_navigation_action


logger = logging.getLogger(__name__)
MAX_RETRIES = 3
MAX_TOOL_CALLS_PER_ROUND = 5
MAX_TOOL_RESPONSE_CHARS = 12_000

_DEFAULT_KEY_INDICES: dict[tuple[str, ...], int] = {}
_DEFAULT_KEY_INDICES_LOCK = Lock()


class AIProviderError(Exception):
    """Safe, user-facing category for an upstream assistant failure."""


class AIConfigurationError(AIProviderError):
    """Raised when Gemini is not configured for this deployment."""


_SAFE_PROVIDER_MESSAGES = frozenset(
    {
        "The AI assistant is not configured: a Gemini API key is required.",
        "The Gemini provider is temporarily unavailable.",
        "The Gemini provider is temporarily unavailable after rate limits.",
        "The AI assistant returned an empty response.",
        "The Gemini provider returned an empty response.",
        "The Gemini provider did not finish the request.",
    }
)


def safe_provider_message(error: AIProviderError) -> str:
    """Return only provider messages owned by this boundary."""

    message = str(error)
    if message in _SAFE_PROVIDER_MESSAGES:
        return message
    return "The Gemini provider is temporarily unavailable."


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
        uses_default_settings = settings is None
        self.settings = settings or get_settings()
        self._api_keys = self._configured_api_keys(api_key)
        self._shared_rotation = (
            uses_default_settings and api_key is None and client is None
        )
        self._key_index = self._initial_key_index()
        self._api_key = self._api_keys[0] if self._api_keys else ""
        self._injected_client = client
        self._client = client
        self._clients: dict[int, Any] = {}
        self._model = model or self.settings.gemini_model or "gemini-3.6-flash"

    def _initial_key_index(self) -> int:
        """Start default application providers at the current key-ring slot."""

        if not self._api_keys or not self._shared_rotation:
            return 0
        with _DEFAULT_KEY_INDICES_LOCK:
            return _DEFAULT_KEY_INDICES.get(self._api_keys, 0) % len(self._api_keys)

    def _remember_key_index(self, previous_index: int, next_index: int) -> None:
        """Persist a rotation without allowing a stale request to move backward."""

        if not self._shared_rotation:
            return
        with _DEFAULT_KEY_INDICES_LOCK:
            current_index = _DEFAULT_KEY_INDICES.get(self._api_keys, previous_index)
            if current_index == previous_index:
                _DEFAULT_KEY_INDICES[self._api_keys] = next_index

    def _configured_api_keys(self, api_key: str | None) -> tuple[str, ...]:
        """Resolve the ordered key list while retaining legacy compatibility."""

        if api_key is not None:
            values: object = (api_key,)
        else:
            values = getattr(self.settings, "gemini_api_key_list", ())
            if isinstance(values, str):
                values = (values,)
            if not isinstance(values, Sequence):
                values = ()

        keys: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            candidate = value.strip()
            if candidate and candidate not in keys:
                keys.append(candidate)
        if not keys and api_key is None:
            legacy_key = getattr(self.settings, "gemini_api_key", "")
            if isinstance(legacy_key, str) and legacy_key.strip():
                keys.append(legacy_key.strip())
        return tuple(keys)

    def _client_or_raise(self, operation: str) -> Any:
        if self._injected_client is not None:
            return self._injected_client
        if not self._api_keys:
            log_event(
                logger,
                logging.ERROR,
                "gemini_configuration_missing",
                operation=operation,
                key_count=0,
            )
            raise AIConfigurationError(
                "The AI assistant is not configured: a Gemini API key is required."
            )
        if self._key_index in self._clients:
            self._client = self._clients[self._key_index]
            return self._client

        api_key = self._api_keys[self._key_index]
        try:
            client = genai.Client(api_key=api_key)
        except Exception as exc:  # SDK/configuration details must stay private.
            log_event(
                logger,
                logging.ERROR,
                "gemini_client_initialization_failed",
                operation=operation,
                key_index=self._key_index + 1,
                key_count=len(self._api_keys),
                error_type=type(exc).__name__,
            )
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None
        self._clients[self._key_index] = client
        self._client = client
        return self._client

    @staticmethod
    def _is_rate_limited(exc: Exception) -> bool:
        """Recognize SDK 429 responses without inspecting private messages."""

        candidates = [
            getattr(exc, "code", None),
            getattr(exc, "status_code", None),
            getattr(exc, "status", None),
        ]
        response = getattr(exc, "response", None)
        if response is not None:
            candidates.append(getattr(response, "status_code", None))
        return any(value == 429 or value == "429" for value in candidates)

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        """Return only an upstream numeric status for safe diagnostics."""

        candidates = [
            getattr(exc, "code", None),
            getattr(exc, "status_code", None),
            getattr(exc, "status", None),
            getattr(getattr(exc, "response", None), "status_code", None),
        ]
        for value in candidates:
            if isinstance(value, int) and 100 <= value <= 599:
                return value
            if isinstance(value, str) and value.isdigit():
                number = int(value)
                if 100 <= number <= 599:
                    return number
        return None

    def _advance_key(self, operation: str, attempt: int) -> None:
        if not self._api_keys:
            log_event(
                logger,
                logging.WARNING,
                "gemini_key_rotation_unavailable",
                operation=operation,
                attempt=attempt,
                key_count=0,
            )
            return
        previous_index = self._key_index
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        self._remember_key_index(previous_index, self._key_index)
        self._client = None
        log_event(
            logger,
            logging.INFO,
            "gemini_key_rotated",
            operation=operation,
            attempt=attempt,
            from_key_index=previous_index + 1,
            to_key_index=self._key_index + 1,
            key_count=len(self._api_keys),
        )

    def _request_with_retry(
        self,
        operation: str,
        request: Callable[[], Any],
    ) -> Any:
        """Execute one provider request and rotate only on HTTP 429."""

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                response = request()
            except AIProviderError:
                raise
            except Exception as exc:  # SDK details must stay private.
                rate_limited = self._is_rate_limited(exc)
                log_event(
                    logger,
                    logging.WARNING if rate_limited else logging.ERROR,
                    "gemini_request_failed",
                    operation=operation,
                    attempt=attempt,
                    max_retries=MAX_RETRIES,
                    key_index=self._key_index + 1,
                    key_count=len(self._api_keys),
                    rate_limited=rate_limited,
                    error_type=type(exc).__name__,
                    status_code=self._status_code(exc),
                )
                if not rate_limited:
                    raise AIProviderError(
                        "The Gemini provider is temporarily unavailable."
                    ) from None
                if attempt > MAX_RETRIES:
                    log_event(
                        logger,
                        logging.ERROR,
                        "gemini_request_exhausted",
                        operation=operation,
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        key_index=self._key_index + 1,
                        key_count=len(self._api_keys),
                    )
                    raise AIProviderError(
                        "The Gemini provider is temporarily unavailable after rate limits."
                    ) from None
                self._advance_key(operation, attempt)
                continue

            log_event(
                logger,
                logging.INFO,
                "gemini_request_succeeded",
                operation=operation,
                attempt=attempt,
                max_retries=MAX_RETRIES,
                key_index=self._key_index + 1,
                key_count=len(self._api_keys),
            )
            return response

        raise AIProviderError("The Gemini provider is temporarily unavailable.")

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text.strip()
        return ""

    @staticmethod
    def _stream_text(response: Any) -> str:
        """Keep chunk boundaries intact so words do not join in the UI."""

        text = getattr(response, "text", None)
        return text if isinstance(text, str) and text.strip() else ""

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
        response = self._request_with_retry(
            "generate",
            lambda: self._client_or_raise("generate").models.generate_content(
                model=self._model,
                contents=contents,
            ),
        )

        try:
            answer = self._response_text(response)
        except Exception as exc:  # SDK response details must stay private.
            log_event(
                logger,
                logging.ERROR,
                "gemini_response_parse_failed",
                operation="generate",
                key_index=self._key_index + 1,
                key_count=len(self._api_keys),
                error_type=type(exc).__name__,
            )
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None
        if not answer:
            log_event(
                logger,
                logging.ERROR,
                "gemini_response_empty",
                operation="generate",
                key_index=self._key_index + 1,
                key_count=len(self._api_keys),
            )
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
        for attempt in range(1, MAX_RETRIES + 2):
            emitted = False
            try:
                chunks = self._client_or_raise("stream").models.generate_content_stream(
                    model=self._model,
                    contents=contents,
                )
                for chunk in chunks:
                    text = self._stream_text(chunk)
                    if text:
                        emitted = True
                        yield text
            except AIProviderError:
                raise
            except Exception as exc:  # SDK details must stay private.
                rate_limited = self._is_rate_limited(exc)
                log_event(
                    logger,
                    logging.WARNING if rate_limited else logging.ERROR,
                    "gemini_request_failed",
                    operation="stream",
                    attempt=attempt,
                    max_retries=MAX_RETRIES,
                    key_index=self._key_index + 1,
                    key_count=len(self._api_keys),
                    rate_limited=rate_limited,
                    error_type=type(exc).__name__,
                    partial_response=emitted,
                )
                if not rate_limited or emitted:
                    raise AIProviderError(
                        "The Gemini provider is temporarily unavailable."
                    ) from None
                if attempt > MAX_RETRIES:
                    log_event(
                        logger,
                        logging.ERROR,
                        "gemini_request_exhausted",
                        operation="stream",
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        key_index=self._key_index + 1,
                        key_count=len(self._api_keys),
                    )
                    raise AIProviderError(
                        "The Gemini provider is temporarily unavailable after rate limits."
                    ) from None
                self._advance_key("stream", attempt)
                continue

            log_event(
                logger,
                logging.INFO,
                "gemini_request_succeeded",
                operation="stream",
                attempt=attempt,
                max_retries=MAX_RETRIES,
                key_index=self._key_index + 1,
                key_count=len(self._api_keys),
                partial_response=emitted,
            )
            return

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

    @staticmethod
    def _safe_navigation_action(result: object) -> dict[str, object] | None:
        """Expose only the validated internal navigation payload to the UI."""

        return canonical_navigation_action(result)

    @staticmethod
    def _bounded_tool_response(result: object) -> tuple[dict[str, object], bool]:
        """Keep provider tool context bounded even if a tool grows later."""

        try:
            encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            return {"error": "Tool result was not serializable."}, False
        if len(encoded) > MAX_TOOL_RESPONSE_CHARS:
            return {"error": "Tool result exceeded the safe response limit."}, False
        return {"result": result}, True

    @staticmethod
    def _initial_content(
        prompt: str,
        history: Sequence[dict[str, str]],
    ) -> types.Content:
        return types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=_joined_prompt(
                        prompt=prompt,
                        system_instruction=None,
                        history=history,
                    )
                )
            ],
        )

    def _function_response_content(
        self,
        calls: Sequence[ProviderToolCall],
        tool_executor: Callable[[str, dict[str, object]], object],
    ) -> tuple[types.Content, list[dict[str, object]]]:
        """Execute calls and keep only safe activity metadata for the client."""

        events: list[dict[str, object]] = []
        function_parts: list[types.Part] = []
        for call in calls:
            event: dict[str, object] = {
                "name": call.name,
                "status": "completed",
            }
            response: dict[str, object]
            try:
                result = tool_executor(call.name, call.arguments)
                response, response_ok = self._bounded_tool_response(result)
                if not response_ok:
                    event["status"] = "error"
                if call.name == "navigate_to_page":
                    action = self._safe_navigation_action(result)
                    if action is None:
                        raise ValueError("The navigation result was not canonical.")
                    event["action"] = action
                    log_event(
                        logger,
                        logging.INFO,
                        "gemini_navigation_action_validated",
                        operation="assistant_navigation",
                        destination=action["destination"],
                        path=action["path"],
                    )
            except Exception:
                # Tool details are application data; do not reflect them into a
                # provider error or log message.
                event["status"] = "error"
                response = {"error": "Tool request was denied."}
            try:
                function_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response=response,
                    )
                )
            except Exception:
                event["status"] = "error"
                function_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"error": "Tool request was denied."},
                    )
                )
            events.append(event)
        return types.Content(role="user", parts=function_parts), events

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

        events: list[dict[str, object]] = []
        round_count = 1
        try:
            config = self._tool_config(tool_definitions, system_instruction)
            contents = [self._initial_content(prompt, history)]
            round_count = max(1, min(int(max_rounds), 5))
            for round_number in range(1, round_count + 1):
                response = self._request_with_retry(
                    "generate_with_tools",
                    lambda: self._client_or_raise(
                        "generate_with_tools"
                    ).models.generate_content(
                        model=self._model,
                        contents=contents,
                        config=config,
                    ),
                )
                calls = self._tool_calls(response)
                if len(calls) > MAX_TOOL_CALLS_PER_ROUND:
                    log_event(
                        logger,
                        logging.ERROR,
                        "gemini_tool_call_limit_exceeded",
                        operation="generate_with_tools",
                        round=round_number,
                        tool_call_count=len(calls),
                    )
                    raise AIProviderError(
                        "The Gemini provider did not finish the request."
                    )
                log_event(
                    logger,
                    logging.INFO,
                    "gemini_tool_round_completed",
                    operation="generate_with_tools",
                    round=round_number,
                    tool_call_count=len(calls),
                )
                if not calls:
                    text = self._response_text(response)
                    if not text:
                        log_event(
                            logger,
                            logging.ERROR,
                            "gemini_response_empty",
                            operation="generate_with_tools",
                            key_index=self._key_index + 1,
                            key_count=len(self._api_keys),
                        )
                        raise AIProviderError(
                            "The Gemini provider returned an empty response."
                        )
                    log_event(
                        logger,
                        logging.INFO,
                        "gemini_tool_request_completed",
                        operation="generate_with_tools",
                        round=round_number,
                        tool_event_count=len(events),
                    )
                    return ToolAwareResponse(text=text, tool_events=events)

                response_content = None
                candidates = getattr(response, "candidates", None) or []
                if candidates:
                    response_content = getattr(candidates[0], "content", None)
                if response_content is not None:
                    contents.append(response_content)
                function_content, round_events = self._function_response_content(
                    calls,
                    tool_executor,
                )
                events.extend(round_events)
                # The legacy generate-content endpoint used by this provider
                # accepts function responses in a user-role content block.
                contents.append(function_content)
        except AIProviderError:
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "gemini_tool_orchestration_failed",
                operation="generate_with_tools",
                error_type=type(exc).__name__,
            )
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None

        log_event(
            logger,
            logging.ERROR,
            "gemini_tool_orchestration_exhausted",
            operation="generate_with_tools",
            round_count=round_count,
            tool_event_count=len(events),
        )
        raise AIProviderError("The Gemini provider did not finish the request.")

    def stream_with_tools(
        self,
        prompt: str,
        *,
        tool_definitions: Sequence[Mapping[str, object]],
        tool_executor: Callable[[str, dict[str, object]], object],
        system_instruction: str | None = None,
        history: Sequence[dict[str, str]] = (),
        max_rounds: int = 3,
    ) -> Iterator[tuple[str, object]]:
        """Stream text while handling complete legacy function-call chunks."""

        events: list[dict[str, object]] = []
        round_count = 1
        try:
            config = self._tool_config(tool_definitions, system_instruction)
            contents = [self._initial_content(prompt, history)]
            round_count = max(1, min(int(max_rounds), 5))
            for round_number in range(1, round_count + 1):
                calls: list[ProviderToolCall] = []
                response_content = None
                emitted_text = False
                for attempt in range(1, MAX_RETRIES + 2):
                    emitted = False
                    round_calls: list[ProviderToolCall] = []
                    round_response_content = None
                    try:
                        chunks = self._client_or_raise(
                            "stream_with_tools"
                        ).models.generate_content_stream(
                            model=self._model,
                            contents=contents,
                            config=config,
                        )
                        for chunk in chunks:
                            emitted = True
                            chunk_calls = self._tool_calls(chunk)
                            for call in chunk_calls:
                                if call not in round_calls:
                                    round_calls.append(call)
                            if chunk_calls and round_response_content is None:
                                candidates = getattr(chunk, "candidates", None) or []
                                if candidates:
                                    round_response_content = getattr(
                                        candidates[0], "content", None
                                    )
                            if not chunk_calls:
                                text = self._stream_text(chunk)
                                if text:
                                    emitted_text = True
                                    yield "token", {"text": text}
                    except AIProviderError:
                        raise
                    except Exception as exc:
                        rate_limited = self._is_rate_limited(exc)
                        log_event(
                            logger,
                            logging.WARNING if rate_limited else logging.ERROR,
                            "gemini_request_failed",
                            operation="stream_with_tools",
                            attempt=attempt,
                            max_retries=MAX_RETRIES,
                            key_index=self._key_index + 1,
                            key_count=len(self._api_keys),
                            rate_limited=rate_limited,
                            error_type=type(exc).__name__,
                            status_code=self._status_code(exc),
                            partial_response=emitted,
                        )
                        if not rate_limited or emitted:
                            raise AIProviderError(
                                "The Gemini provider is temporarily unavailable."
                            ) from None
                        if attempt > MAX_RETRIES:
                            log_event(
                                logger,
                                logging.ERROR,
                                "gemini_request_exhausted",
                                operation="stream_with_tools",
                                attempt=attempt,
                                max_retries=MAX_RETRIES,
                                key_index=self._key_index + 1,
                                key_count=len(self._api_keys),
                            )
                            raise AIProviderError(
                                "The Gemini provider is temporarily unavailable after rate limits."
                            ) from None
                        self._advance_key("stream_with_tools", attempt)
                        continue

                    calls = round_calls
                    response_content = round_response_content
                    log_event(
                        logger,
                        logging.INFO,
                        "gemini_request_succeeded",
                        operation="stream_with_tools",
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        key_index=self._key_index + 1,
                        key_count=len(self._api_keys),
                        partial_response=emitted,
                    )
                    break

                log_event(
                    logger,
                    logging.INFO,
                    "gemini_tool_round_completed",
                    operation="stream_with_tools",
                    round=round_number,
                    tool_call_count=len(calls),
                )
                if len(calls) > MAX_TOOL_CALLS_PER_ROUND:
                    log_event(
                        logger,
                        logging.ERROR,
                        "gemini_tool_call_limit_exceeded",
                        operation="stream_with_tools",
                        round=round_number,
                        tool_call_count=len(calls),
                    )
                    raise AIProviderError(
                        "The Gemini provider did not finish the request."
                    )
                if not calls:
                    if not emitted_text:
                        log_event(
                            logger,
                            logging.ERROR,
                            "gemini_response_empty",
                            operation="stream_with_tools",
                            key_index=self._key_index + 1,
                            key_count=len(self._api_keys),
                        )
                        raise AIProviderError(
                            "The Gemini provider returned an empty response."
                        )
                    log_event(
                        logger,
                        logging.INFO,
                        "gemini_tool_request_completed",
                        operation="stream_with_tools",
                        round=round_number,
                        tool_event_count=len(events),
                    )
                    return
                if response_content is None:
                    raise AIProviderError(
                        "The Gemini provider did not return a function-call response."
                    )
                function_content, round_events = self._function_response_content(
                    calls,
                    tool_executor,
                )
                events.extend(round_events)
                for event in round_events:
                    yield "tool", event
                contents.append(response_content)
                contents.append(function_content)
        except AIProviderError:
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "gemini_tool_orchestration_failed",
                operation="stream_with_tools",
                error_type=type(exc).__name__,
            )
            raise AIProviderError(
                "The Gemini provider is temporarily unavailable."
            ) from None

        log_event(
            logger,
            logging.ERROR,
            "gemini_tool_orchestration_exhausted",
            operation="stream_with_tools",
            round_count=round_count,
            tool_event_count=len(events),
        )
        raise AIProviderError("The Gemini provider did not finish the request.")


# The short alias makes dependency injection pleasant in route/service tests.
GeminiChatProvider = GeminiProvider
