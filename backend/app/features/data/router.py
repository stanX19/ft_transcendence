"""Librarian/admin catalog import and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.features.data.schemas import CatalogFormat, ImportIssue, ImportResult
from app.features.data.service import (
    CatalogDataError,
    detect_format,
    export_catalog,
    parse_catalog,
    validate_and_apply_import,
)
from app.features.users.models import User


router = APIRouter(prefix="/api/admin/import-export", tags=["catalog data"])

_MEDIA_TYPES = {
    CatalogFormat.CSV: "text/csv; charset=utf-8",
    CatalogFormat.JSON: "application/json; charset=utf-8",
    CatalogFormat.XML: "application/xml; charset=utf-8",
}


def _result(
    format: CatalogFormat,
    *,
    inserted: int,
    updated: int,
    rejected: int,
    errors: list[ImportIssue],
    error: dict[str, str] | None = None,
) -> dict[str, object]:
    counts = {"inserted": inserted, "updated": updated, "rejected": rejected}
    result: dict[str, object] = {
        "format": format.value,
        **counts,
        "errors": [issue.model_dump() for issue in errors],
        "summary": counts,
    }
    if error is not None:
        result["error"] = error
    return result


@router.get(
    "/export",
    summary="Export the catalog",
    description="Download the complete catalog as CSV, JSON, or XML.",
)
def export_catalog_route(
    format: str = Query(
        default="json",
        description="Export format: csv, json, or xml.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("LIBRARIAN", "ADMIN")),
) -> Response:
    del current_user
    try:
        selected_format = CatalogFormat(format.strip().lower())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from None
    content = export_catalog(db, selected_format)
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[selected_format],
        headers={
            "Content-Disposition": (
                f'attachment; filename="libraryos-catalog.{selected_format.value}"'
            )
        },
    )


@router.post(
    "/import",
    response_model=ImportResult,
    status_code=status.HTTP_200_OK,
    summary="Import catalog records",
    description="Validate a complete CSV, JSON, or XML upload, then apply it atomically.",
)
async def import_catalog_route(
    file: UploadFile = File(..., description="A CSV, JSON, or XML catalog document."),
    format_query: str | None = Query(default=None, alias="format"),
    format_form: str | None = Form(default=None, alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("LIBRARIAN", "ADMIN")),
) -> ImportResult | JSONResponse:
    del current_user
    settings = get_settings()
    max_bytes = settings.upload_max_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    await file.close()
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        selected_format = detect_format(
            format_form or format_query,
            file.filename,
            file.content_type,
        )
        records = parse_catalog(data, selected_format)
    except CatalogDataError as exc:
        issue = ImportIssue(record=exc.record, message=exc.message)
        selected_format = CatalogFormat.JSON
        try:
            selected_format = detect_format(
                format_form or format_query,
                file.filename,
                file.content_type,
            )
        except CatalogDataError:
            pass
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_result(
                selected_format,
                inserted=0,
                updated=0,
                rejected=1,
                errors=[issue],
                error={
                    "code": "validation_error",
                    "message": "The catalog document could not be validated.",
                },
            ),
        )

    inserted, updated, issues = validate_and_apply_import(db, records)
    if issues:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_result(
                selected_format,
                inserted=0,
                updated=0,
                rejected=len(issues),
                errors=issues,
                error={
                    "code": "validation_error",
                    "message": "The catalog import was not applied because validation failed.",
                },
            ),
        )
    return ImportResult(
        **_result(
            selected_format,
            inserted=inserted,
            updated=updated,
            rejected=0,
            errors=[],
        )
    )
