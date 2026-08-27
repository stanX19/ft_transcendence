"""Deterministic PostgreSQL test-database bootstrap.

The protected API test helper intentionally only starts PostgreSQL and runs
pytest.  This session hook applies the current Alembic head to the isolated
test database before collection, so tests never depend on the development
database having been migrated first.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


os.environ.setdefault("APP_ENV", "test")


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
