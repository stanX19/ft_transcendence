"""Consistent, safe JSON error responses for the API."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)

_HTTP_ERROR_MESSAGES: Mapping[int, tuple[str, str]] = {
    400: ("invalid_request", "The request is invalid."),
    401: ("unauthenticated", "Authentication is required."),
    403: ("forbidden", "You do not have permission to perform this action."),
    404: ("not_found", "The requested resource was not found."),
    409: ("conflict", "The request conflicts with the current state."),
    422: ("validation_error", "The request contains invalid or missing values."),
    429: ("rate_limited", "Too many requests."),
}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Return stable messages without reflecting arbitrary exception detail."""

    del request
    code, message = _HTTP_ERROR_MESSAGES.get(
        exc.status_code,
        ("http_error", "The request could not be completed."),
    )
    return _error_response(exc.status_code, code, message)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Normalize FastAPI/Pydantic request validation failures."""

    del request, exc
    return _error_response(
        422,
        "validation_error",
        "The request contains invalid or missing values.",
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Hide internal details while retaining a safe server-side diagnostic."""

    del request
    # Exception messages may contain credentials or user input, so only the
    # type is recorded and neither the message nor traceback is reflected.
    logger.error("Unhandled application exception: %s", type(exc).__name__)
    return _error_response(
        500,
        "internal_error",
        "An unexpected server error occurred.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install the API-wide exception handlers on an application instance."""

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
