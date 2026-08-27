"""Database contracts for the user model and its first migration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


EXPECTED_USER_COLUMNS = {
    "id",
    "email",
    "password_hash",
    "display_name",
    "bio",
    "role",
    "last_seen_at",
    "created_at",
    "updated_at",
}


def _new_user(email: str, *, role: str = "MEMBER"):
    from app.features.users.models import User

    return User(
        email=email,
        password_hash="$argon2id$v=19$test-only-hash",
        display_name="Model Test User",
        bio="",
        role=role,
        last_seen_at=datetime.now(timezone.utc),
    )


def test_users_model_is_registered_before_alembic_imports_metadata() -> None:
    """A fresh registry import must discover User without an app-side import."""

    backend_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["APP_ENV"] = "test"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.core.model_registry import Base; "
                "assert 'users' in Base.metadata.tables"
            ),
        ],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_users_table_has_profile_role_presence_and_timestamp_columns() -> None:
    from app.core.database import Base, engine
    from app.features.users.models import User

    assert User.__table__ is Base.metadata.tables["users"]

    columns = inspect(engine).get_columns("users")
    assert {column["name"] for column in columns} >= EXPECTED_USER_COLUMNS

    table = User.__table__
    assert table.c.email.unique or any(
        constraint.columns.keys() == ["email"]
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    )
    assert not {"avatar_file_id", "cover_file_id"}.intersection(table.c.keys())

    for name in ("last_seen_at", "created_at", "updated_at"):
        assert getattr(table.c[name].type, "timezone", False), name


def test_email_is_unique_and_role_defaults_to_member(
    db_session,
    unique_email,
) -> None:
    from app.features.users.models import User

    first_email = unique_email("duplicate")
    first = _new_user(first_email)
    db_session.add(first)
    db_session.commit()
    db_session.refresh(first)

    assert getattr(first.role, "value", first.role) == "MEMBER"
    assert first.created_at is not None
    assert first.updated_at is not None
    assert first.last_seen_at is not None

    duplicate = _new_user(first_email)
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_database_rejects_roles_outside_the_three_supported_values(
    db_session,
    unique_email,
) -> None:
    db_session.add(_new_user(unique_email("invalid-role"), role="NOT_A_ROLE"))

    with pytest.raises(SQLAlchemyError):
        db_session.commit()
