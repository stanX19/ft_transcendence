"""Authenticated POST-SSE chat transport for the LibraryOS assistant."""

from __future__ import annotations

import json
from collections.abc import Iterator
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.ai.provider import AIProviderError, safe_provider_message
from app.features.ai.rate_limit import enforce_ai_rate_limit
from app.features.ai.schemas import ChatRequest
from app.features.ai.service import AssistantOrchestrator
from app.features.ai.telemetry import bind_request_id, log_event, new_request_id
from app.features.users.models import User


router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger(__name__)


def _sse(event: str, payload: object) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


def _stream_chat(
    request: ChatRequest,
    *,
    db: Session,
    current_user: User,
    request_id: str,
) -> Iterator[str]:
    orchestrator = AssistantOrchestrator(db, current_user)
    history = request.history_payload()
    with bind_request_id(request_id):
        log_event(
            logger,
            logging.INFO,
            "assistant_stream_started",
            operation="assistant",
            message_length=len(request.text),
            history_count=len(history),
        )
    stream = orchestrator.stream(request.text, history=history)
    while True:
        try:
            with bind_request_id(request_id):
                event, payload = next(stream)
        except StopIteration:
            with bind_request_id(request_id):
                log_event(
                    logger,
                    logging.INFO,
                    "assistant_stream_completed",
                    operation="assistant",
                )
            return
        except AIProviderError as exc:
            # Provider exceptions have already been translated to safe messages.
            with bind_request_id(request_id):
                log_event(
                    logger,
                    logging.ERROR,
                    "assistant_stream_failed",
                    operation="assistant",
                    failure_type=type(exc).__name__,
                    failure_code="provider_error",
                )
            yield _sse(
                "error",
                {"code": "provider_error", "message": safe_provider_message(exc)},
            )
            return
        except Exception as exc:
            with bind_request_id(request_id):
                log_event(
                    logger,
                    logging.ERROR,
                    "assistant_stream_failed",
                    operation="assistant",
                    failure_type=type(exc).__name__,
                    failure_code="assistant_error",
                )
            yield _sse(
                "error",
                {
                    "code": "assistant_error",
                    "message": "The assistant could not complete this request.",
                },
            )
            return

        yield _sse(event, payload)


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def chat_stream(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(enforce_ai_rate_limit),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream assistant source, tool, token, and terminal SSE events."""

    request_id = getattr(http_request.state, "request_id", None) or new_request_id()
    return StreamingResponse(
        _stream_chat(
            request,
            db=db,
            current_user=current_user,
            request_id=request_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


__all__ = ["router"]
