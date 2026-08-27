"""Database URL selection contract for isolated backend tests.

The foundation implementation is expected to expose ``Settings`` from
``app.core.config`` and ``get_database_url(settings)`` from
``app.core.database``.  Keeping the selection at this boundary makes it
possible to prove that the SQLAlchemy engine cannot silently use the normal
database during a test run.
"""

from __future__ import annotations

from typing import Literal

import pytest

from app.core.config import Settings
from app.core.database import get_database_url


NORMAL_DATABASE_URL = "postgresql+psycopg://normal-db/libraryos"
TEST_DATABASE_URL = "postgresql+psycopg://test-db/libraryos_test"


def _settings_from_environment(
    monkeypatch,
    app_env: Literal["development", "test"],
) -> Settings:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", NORMAL_DATABASE_URL)
    monkeypatch.setenv("TEST_DATABASE_URL", TEST_DATABASE_URL)
    return Settings(_env_file=None)


def test_test_environment_selects_test_database_url(monkeypatch) -> None:
    settings = _settings_from_environment(monkeypatch, "test")

    assert get_database_url(settings) == TEST_DATABASE_URL
    assert get_database_url(settings) != NORMAL_DATABASE_URL


def test_development_environment_selects_normal_database_url(monkeypatch) -> None:
    settings = _settings_from_environment(monkeypatch, "development")

    assert get_database_url(settings) == NORMAL_DATABASE_URL
    assert get_database_url(settings) != TEST_DATABASE_URL


def test_production_rejects_documented_placeholder_secrets(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET", "replace_me_with_a_long_random_development_secret")
    monkeypatch.setenv("PUBLIC_API_KEY", "replace_me_public_api_key")

    with pytest.raises(ValueError, match="AUTH_SECRET"):
        Settings(_env_file=None)
