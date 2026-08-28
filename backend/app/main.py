"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from app.core.errors import register_error_handlers
from app.features.auth.router import router as auth_router
from app.features.admin.router import router as admin_router
from app.features.books.router import router as books_router
from app.features.files.router import router as files_router
from app.features.friends.router import router as friends_router
from app.features.loans.router import router as loans_router
from app.features.public_api.router import router as public_api_router
from app.features.data.router import router as data_router
from app.features.ai.router import router as ai_router
from app.features.ai.telemetry import new_request_id
from app.features.users.router import router as users_router


def create_app() -> FastAPI:
    """Build the application and register foundation routes and handlers."""

    # AI lifecycle events are intentionally visible at normal service log
    # level; they contain only the allowlisted fields from ``telemetry.py``.
    ai_logger = logging.getLogger("app.features.ai")
    ai_logger.setLevel(logging.INFO)
    if not any(
        getattr(handler, "_libraryos_ai_handler", False)
        for handler in ai_logger.handlers
    ):
        ai_handler = logging.StreamHandler()
        ai_handler.setLevel(logging.INFO)
        ai_handler.setFormatter(logging.Formatter("%(message)s"))
        ai_handler._libraryos_ai_handler = True
        ai_logger.addHandler(ai_handler)

    app = FastAPI(
        title="LibraryOS API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        """Give every response a server-owned correlation ID."""

        request_id = new_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        return response

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(books_router)
    app.include_router(files_router)
    app.include_router(friends_router)
    app.include_router(loans_router)
    app.include_router(public_api_router)
    app.include_router(data_router)
    app.include_router(ai_router)
    app.include_router(users_router)

    @app.get("/api/health", tags=["foundation"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
