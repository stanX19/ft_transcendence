"""Deterministic PostgreSQL test-database bootstrap.

The protected API test helper intentionally only starts PostgreSQL and runs
pytest.  This session hook applies the current Alembic head to the isolated
test database before collection, so tests never depend on the development
database having been migrated first.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


os.environ.setdefault("APP_ENV", "test")


@pytest.fixture
def app() -> FastAPI:
    """Return the shared application instance used by API contract tests."""

    from app.main import app as application

    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Use HTTPS so Secure session-cookie behavior is exercised by default."""

    with TestClient(
        app,
        base_url="https://testserver",
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


@pytest.fixture
def client_factory(app: FastAPI) -> Iterator[Callable[[], TestClient]]:
    """Create independent HTTPS clients for multi-user/authentication tests."""

    clients: list[TestClient] = []

    def make_client() -> TestClient:
        test_client = TestClient(
            app,
            base_url="https://testserver",
            raise_server_exceptions=False,
        )
        clients.append(test_client)
        return test_client

    yield make_client

    for test_client in clients:
        test_client.close()


@pytest.fixture
def unique_email() -> Callable[[str], str]:
    """Return unique addresses so tests can share the isolated DB safely."""

    def make_email(label: str = "qa-user") -> str:
        return f"{label}-{uuid4().hex}@example.test"

    return make_email


@pytest.fixture
def register_user(
    unique_email: Callable[[str], str],
) -> Callable[..., object]:
    """Register a user through the public API using caller-supplied client state."""

    def register(
        test_client: TestClient,
        *,
        email: str | None = None,
        password: str = "correct-horse-battery-staple",
        display_name: str = "QA Reader",
    ) -> object:
        return test_client.post(
            "/api/auth/register",
            json={
                "email": email or unique_email("auth-user"),
                "password": password,
                "display_name": display_name,
            },
        )

    return register


@pytest.fixture
def login_user() -> Callable[..., object]:
    """Log in through the public API without coupling tests to response shape."""

    def login(
        test_client: TestClient,
        *,
        email: str,
        password: str = "correct-horse-battery-staple",
    ) -> object:
        return test_client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    return login


@pytest.fixture
def db_session() -> Iterator[object]:
    """Yield a real PostgreSQL session for persistence/constraint assertions."""

    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def app_with_temporary_routes(app: FastAPI) -> Iterator[FastAPI]:
    """Allow dependency tests to add a route without leaking it to other tests."""

    original_routes = list(app.router.routes)
    try:
        yield app
    finally:
        app.router.routes[:] = original_routes


def pytest_sessionstart(session) -> None:
    del session
    if os.environ.get("APP_ENV") != "test":
        raise RuntimeError("Backend tests must run with APP_ENV=test.")

    backend_root = Path(__file__).resolve().parent.parent
    last_error: subprocess.CalledProcessError | None = None
    for _ in range(30):
        try:
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=backend_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(
        "Could not migrate the isolated test database after 30 attempts."
    ) from last_error
