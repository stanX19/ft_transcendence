"""Validation, replacement, and metadata operations for uploaded files."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.files.models import FileAsset, FileKind
from app.features.files.storage import delete_bytes, save_bytes


class InvalidFile(Exception):
    """Raised when uploaded bytes do not match the requested asset contract."""


def _image_format(content: bytes) -> str:
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            image_format = (image.format or "").upper()
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ):
        raise InvalidFile("The image content is invalid.") from None
    if image_format not in {"JPEG", "PNG", "WEBP"}:
        raise InvalidFile("This image format is not supported.")
    return image_format


def _validate_content(content: bytes, kind: FileKind) -> tuple[str, str]:
    maximum = get_settings().upload_max_mb * 1024 * 1024
    if not content or len(content) > maximum:
        raise InvalidFile("The file is empty or exceeds the configured size limit.")

    if kind in {FileKind.AVATAR, FileKind.BOOK_COVER}:
        image_format = _image_format(content)
        extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]
        mime = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }[image_format]
        return mime, extension

    if content.startswith(b"%PDF-") and b"%%EOF" in content[-1024:]:
        return "application/pdf", ".pdf"
    raise InvalidFile("The PDF content is invalid.")


def _current_asset(
    db: Session,
    *,
    kind: FileKind,
    owner_user_id: int | None = None,
    book_id: int | None = None,
) -> FileAsset | None:
    statement = select(FileAsset).where(FileAsset.kind == kind.value)
    if owner_user_id is not None:
        statement = statement.where(FileAsset.owner_user_id == owner_user_id)
    if book_id is not None:
        statement = statement.where(FileAsset.book_id == book_id)
    return db.scalar(statement)


def current_avatar(db: Session, user_id: int) -> FileAsset | None:
    """Return the one current avatar for a user, if present."""

    return _current_asset(db, kind=FileKind.AVATAR, owner_user_id=user_id)


def current_book_cover(db: Session, book_id: int) -> FileAsset | None:
    """Return the one current cover for a book, if present."""

    return _current_asset(db, kind=FileKind.BOOK_COVER, book_id=book_id)


def serialize_asset(asset: FileAsset) -> dict[str, object]:
    """Expose metadata and an id-based URL, never a storage path."""

    return {
        "id": asset.id,
        "owner_user_id": asset.owner_user_id,
        "book_id": asset.book_id,
        "kind": asset.kind,
        "original_filename": asset.original_filename,
        "stored_filename": asset.stored_filename,
        "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes,
        "created_at": asset.created_at,
        "url": f"/api/files/{asset.id}",
    }


def save_uploaded_file(
    db: Session,
    *,
    content: bytes,
    original_filename: str | None,
    kind: FileKind,
    owner_user_id: int | None = None,
    book_id: int | None = None,
) -> FileAsset:
    """Validate, persist, and atomically replace the current avatar or cover."""

    if (owner_user_id is None) == (book_id is None):
        raise InvalidFile("A file must belong to exactly one owner.")
    mime_type, extension = _validate_content(content, kind)
    stored_filename = save_bytes(content, extension)
    previous = None
    if kind == FileKind.AVATAR:
        previous = current_avatar(db, owner_user_id or 0)
    elif kind == FileKind.BOOK_COVER:
        previous = current_book_cover(db, book_id or 0)

    asset = FileAsset(
        owner_user_id=owner_user_id,
        book_id=book_id,
        kind=kind.value,
        original_filename=(original_filename or "upload")[:255],
        stored_filename=stored_filename,
        mime_type=mime_type,
        size_bytes=len(content),
    )
    try:
        if previous is not None:
            db.delete(previous)
            # Delete first so the partial unique index permits the replacement
            # within the same transaction on PostgreSQL.
            db.flush()
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        delete_bytes(stored_filename)
        raise

    if previous is not None:
        delete_bytes(previous.stored_filename)
    return asset


def delete_asset(db: Session, asset: FileAsset) -> None:
    """Remove metadata transactionally, then clean up the stored bytes."""

    stored_filename = asset.stored_filename
    db.delete(asset)
    db.commit()
    delete_bytes(stored_filename)


def parse_book_kind(value: str) -> FileKind:
    """Parse the limited book upload kind accepted by the multipart API."""

    try:
        kind = FileKind(value.strip().upper())
    except ValueError:
        raise InvalidFile("Unsupported book file kind.") from None
    if kind == FileKind.AVATAR:
        raise InvalidFile("Avatars belong to user uploads.")
    return kind
