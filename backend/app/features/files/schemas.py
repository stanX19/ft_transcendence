"""Transport schemas for safe file metadata responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FileAssetResponse(BaseModel):
    id: int
    owner_user_id: int | None
    book_id: int | None
    kind: str
    original_filename: str
    stored_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    url: str


class FileEnvelope(BaseModel):
    file: FileAssetResponse
