"""Authenticated POST-SSE chat transport for the LibraryOS assistant."""

from __future__ import annotations

import json
from collections.abc import Iterator
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.features.ai.provider import AIProviderError
from app.features.ai.schemas import ChatRequest
from app.features.ai.service import AssistantOrchestrator
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
) -> Iterator[str]:
    orchestrator = AssistantOrchestrator(db, current_user)
    try:
        for event, payload in orchestrator.stream(
            request.text,
            history=request.history_payload(),
        ):
            yield _sse(event, payload)
    except AIProviderError as exc:
        # Provider exceptions have already been translated to safe messages.
        yield _sse("error", {"code": "provider_error", "message": str(exc)})
    except Exception as exc:
        logger.error("Assistant stream failed: %s", type(exc).__name__)
        yield _sse(
            "error",
            {
                "code": "assistant_error",
                "message": "The assistant could not complete this request.",
            },
        )


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream assistant source, tool, token, and terminal SSE events."""

    return StreamingResponse(
        _stream_chat(request, db=db, current_user=current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
