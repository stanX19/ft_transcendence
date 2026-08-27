"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router


def create_app() -> FastAPI:
    """Build the application and register foundation routes and handlers."""

    app = FastAPI(
        title="LibraryOS API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(users_router)

    @app.get("/api/health", tags=["foundation"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
