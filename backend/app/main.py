"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.errors import register_error_handlers


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

    @app.get("/api/health", tags=["foundation"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
