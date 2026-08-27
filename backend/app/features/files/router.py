"""Secure multipart upload and id-based file serving routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as PathParam, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user, require_roles
from app.features.books.models import Book
from app.features.files.models import FileAsset, FileKind
from app.features.files.schemas import FileAssetResponse, FileEnvelope
from app.features.files.service import (
    InvalidFile,
    current_avatar,
    delete_asset,
    parse_book_kind,
    save_uploaded_file,
    serialize_asset,
)
from app.features.files.storage import FileStorageError, safe_stored_path
from app.features.users.models import User


router = APIRouter(tags=["files"])


async def _read_upload(file: UploadFile) -> bytes:
    from app.core.config import get_settings

    limit = get_settings().upload_max_mb * 1024 * 1024
    return await file.read(limit + 1)


@router.post(
    "/api/users/me/avatar",
    response_model=FileEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileEnvelope:
    try:
        asset = save_uploaded_file(
            db,
            content=await _read_upload(file),
            original_filename=file.filename,
            kind=FileKind.AVATAR,
            owner_user_id=current_user.id,
        )
    except InvalidFile:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from None
    return FileEnvelope(file=FileAssetResponse.model_validate(serialize_asset(asset)))


@router.delete("/api/users/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    asset = current_avatar(db, current_user.id)
    if asset is not None:
        delete_asset(db, asset)


@router.post(
    "/api/books/{book_id}/files",
    response_model=FileEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def upload_book_file(
    book_id: int = PathParam(..., gt=0),
    kind: str = Form(default=FileKind.BOOK_COVER.value),
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("LIBRARIAN", "ADMIN")),
    db: Session = Depends(get_db),
) -> FileEnvelope:
    del current_user
    if db.get(Book, book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        asset_kind = parse_book_kind(kind)
        asset = save_uploaded_file(
            db,
            content=await _read_upload(file),
            original_filename=file.filename,
            kind=asset_kind,
            book_id=book_id,
        )
    except InvalidFile:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from None
    return FileEnvelope(file=FileAssetResponse.model_validate(serialize_asset(asset)))


@router.get("/api/files/{file_id}")
def read_file(
    file_id: int = PathParam(..., gt=0),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    asset = db.get(FileAsset, file_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if asset.kind == FileKind.BOOK_DOCUMENT.value and current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        path = safe_stored_path(asset.stored_filename)
    except FileStorageError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    download_name = Path(asset.original_filename.replace("\\", "/")).name
    download_name = "".join(
        character for character in download_name if ord(character) >= 32 and ord(character) != 127
    )[:255] or "download"
    return FileResponse(path, media_type=asset.mime_type, filename=download_name)


@router.delete(
    "/api/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_book_file(
    file_id: int = PathParam(..., gt=0),
    current_user: User = Depends(require_roles("LIBRARIAN", "ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    del current_user
    asset = db.get(FileAsset, file_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if asset.book_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    delete_asset(db, asset)
