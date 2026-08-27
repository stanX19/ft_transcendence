"""Shared setup for the foundation contract tests.

These tests must never accidentally initialize the application against the
normal development database.  The Docker test command supplies real values;
the harmless local defaults only make import/collection safe before Docker is
running.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


# Force the test environment before any test imports app.main or the settings
# singleton.  A developer's shell may otherwise contain APP_ENV=development.
os.environ["APP_ENV"] = "test"
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://normal-db/libraryos"
)
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://test-db/libraryos_test"
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Return an HTTPS TestClient with server exceptions rendered as HTTP."""

    from app.main import app

    with TestClient(
        app,
        base_url="https://testserver",
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client
