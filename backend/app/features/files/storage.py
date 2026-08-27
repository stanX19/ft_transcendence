"""Small safe-path boundary for the persistent uploads volume."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Raised when a stored filename cannot be resolved safely."""


def storage_root() -> Path:
    """Return and create the configured private storage directory."""

    root = Path(get_settings().upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_stored_path(stored_filename: str) -> Path:
    """Resolve a generated filename while rejecting traversal or escapes."""

    if (
        not stored_filename
        or Path(stored_filename).name != stored_filename
        or "/" in stored_filename
        or "\\" in stored_filename
    ):
        raise FileStorageError("Unsafe stored filename.")
    root = storage_root()
    candidate = (root / stored_filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise FileStorageError("Stored file escaped its root.") from exc
    return candidate


def save_bytes(content: bytes, extension: str) -> str:
    """Write bytes under a random server-generated name and return that name."""

    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    stored_filename = f"{uuid4().hex}{normalized_extension.lower()}"
    safe_stored_path(stored_filename).write_bytes(content)
    return stored_filename


def delete_bytes(stored_filename: str) -> None:
    """Delete one stored file, treating an already-missing file as cleaned up."""

    try:
        path = safe_stored_path(stored_filename)
    except FileStorageError:
        logger.warning("Could not resolve stored file for cleanup.")
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove stored file after metadata change.")
