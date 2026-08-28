"""Small, privacy-safe telemetry helpers for assistant requests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import json
import logging
import re
from typing import Any
from uuid import uuid4


_REQUEST_ID: ContextVar[str | None] = ContextVar("ai_request_id", default=None)
_SAFE_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")
_SAFE_FIELDS = {
    "answer_length",
    "attempt",
    "failure_code",
    "failure_type",
    "from_key_index",
    "history_count",
    "key_count",
    "key_index",
    "max_retries",
    "message_length",
    "operation",
    "partial_response",
    "query_length",
    "rate_limited",
    "retrieval_limit",
    "round",
    "round_count",
    "source_count",
    "status_code",
    "to_key_index",
    "tool_call_count",
    "tool_event_count",
    "error_type",
}


def new_request_id() -> str:
    """Create a server-owned correlation ID."""

    return uuid4().hex


def normalize_request_id(value: str | None) -> str:
    """Accept only server-shaped IDs; untrusted values become fresh IDs."""

    candidate = value.strip() if isinstance(value, str) else ""
    if _SAFE_REQUEST_ID.fullmatch(candidate):
        return candidate
    return new_request_id()


def current_request_id() -> str:
    """Return the current AI correlation ID, creating one for direct callers."""

    value = _REQUEST_ID.get()
    if value is None:
        value = new_request_id()
        _REQUEST_ID.set(value)
    return value


@contextmanager
def bind_request_id(value: str | None = None) -> Iterator[str]:
    """Bind one correlation ID across a streamed assistant request."""

    token = _REQUEST_ID.set(normalize_request_id(value))
    try:
        yield current_request_id()
    finally:
        _REQUEST_ID.reset(token)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Write one stable JSON event without prompts, secrets, or PII."""

    payload: dict[str, object] = {
        "event": event,
        "request_id": current_request_id(),
    }
    for name, value in fields.items():
        if name not in _SAFE_FIELDS or value is None:
            continue
        if isinstance(value, (bool, int, float, str)):
            payload[name] = value
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


__all__ = [
    "bind_request_id",
    "current_request_id",
    "log_event",
    "new_request_id",
    "normalize_request_id",
]
