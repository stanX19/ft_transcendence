"""Safe catalog serialization, parsing, and atomic bulk application."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import io
import json
import re
from typing import Any
from xml.etree import ElementTree

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.books.models import Book
from app.features.books.schemas import BookCreate, BookUpdate
from app.features.books.service import (
    BookInventoryConflict,
    create_book,
    update_book,
)
from app.features.data.schemas import CatalogFormat, ImportIssue


BOOK_FIELDS = (
    "id",
    "isbn",
    "slug",
    "title",
    "author",
    "description",
    "category",
    "publication_year",
    "total_copies",
    "available_copies",
    "created_at",
    "updated_at",
)
WRITABLE_FIELDS = {
    "isbn",
    "slug",
    "title",
    "author",
    "description",
    "category",
    "publication_year",
    "total_copies",
    "available_copies",
}
INTEGER_FIELDS = {
    "id",
    "publication_year",
    "total_copies",
    "available_copies",
}
_XML_DANGEROUS_INPUT = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class CatalogDataError(Exception):
    """Raised when an exchange document cannot be parsed or validated."""

    def __init__(self, message: str, *, record: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.record = record


class CatalogDataConflict(Exception):
    """Raised when an otherwise valid import conflicts during application."""

    def __init__(self, message: str, *, record: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.record = record


@dataclass
class _ImportPlan:
    record_number: int
    payload: BookCreate | BookUpdate
    existing: Book | None


def coerce_format(value: CatalogFormat | str | None) -> CatalogFormat:
    """Normalize a format supplied by a query, form, or file extension."""

    if isinstance(value, CatalogFormat):
        return value
    if isinstance(value, str):
        try:
            return CatalogFormat(value.strip().lower())
        except ValueError:
            pass
    raise CatalogDataError("Format must be one of csv, json, or xml.")


def detect_format(
    explicit_format: CatalogFormat | str | None,
    filename: str | None,
    content_type: str | None,
) -> CatalogFormat:
    """Choose an explicit format first, then a safe extension/content-type hint."""

    if explicit_format is not None:
        return coerce_format(explicit_format)
    suffix = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if suffix in {item.value for item in CatalogFormat}:
        return CatalogFormat(suffix)
    content_type_value = (content_type or "").split(";", 1)[0].strip().lower()
    content_types = {
        "text/csv": CatalogFormat.CSV,
        "application/json": CatalogFormat.JSON,
        "application/xml": CatalogFormat.XML,
        "text/xml": CatalogFormat.XML,
    }
    if content_type_value in content_types:
        return content_types[content_type_value]
    raise CatalogDataError("Choose CSV, JSON, or XML for the catalog file.")


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _book_record(book: Book) -> dict[str, Any]:
    return {
        "id": book.id,
        "isbn": book.isbn,
        "slug": book.slug,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "category": book.category,
        "publication_year": book.publication_year,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "created_at": _isoformat(book.created_at),
        "updated_at": _isoformat(book.updated_at),
    }


def export_catalog(db: Session, format: CatalogFormat) -> str:
    """Serialize every catalog row in a stable id order."""

    records = [
        _book_record(book)
        for book in db.scalars(select(Book).order_by(Book.id)).all()
    ]
    if format is CatalogFormat.JSON:
        return json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    if format is CatalogFormat.CSV:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=BOOK_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()

    root = ElementTree.Element("books")
    for record in records:
        book_element = ElementTree.SubElement(root, "book")
        for field in BOOK_FIELDS:
            value = record[field]
            child = ElementTree.SubElement(book_element, field)
            if value is None:
                child.set("null", "true")
            else:
                child.text = str(value)
    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(root, encoding="unicode") + "\n"


def _csv_value(field: str, value: str | None) -> Any:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if field in INTEGER_FIELDS:
        try:
            return int(stripped)
        except ValueError:
            return stripped
    return value


def _parse_json(text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogDataError("The JSON document is not valid.") from exc
    if isinstance(parsed, dict):
        parsed = parsed.get("books", parsed.get("items"))
    if not isinstance(parsed, list):
        raise CatalogDataError("JSON must contain a list of book records.")
    records: list[dict[str, Any]] = []
    for index, record in enumerate(parsed, start=1):
        if not isinstance(record, dict):
            raise CatalogDataError("Each JSON book record must be an object.", record=index)
        records.append(record)
    return records


def _parse_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise CatalogDataError("The CSV document must include a header row.")
    fields = {field.strip() for field in reader.fieldnames if field is not None}
    missing = {"title", "author", "description", "category", "total_copies"} - fields
    if missing:
        raise CatalogDataError(
            "CSV is missing required columns: " + ", ".join(sorted(missing)) + "."
        )
    if None in reader.fieldnames:
        raise CatalogDataError("CSV contains an unnamed column.")
    records: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=1):
        if None in row:
            raise CatalogDataError("CSV contains more values than its header.", record=index)
        record = {
            key.strip(): _csv_value(key.strip(), value)
            for key, value in row.items()
            if key is not None
        }
        records.append(record)
    return records


def _parse_xml(text: str) -> list[dict[str, Any]]:
    if _XML_DANGEROUS_INPUT.search(text):
        raise CatalogDataError("XML document types and entities are not supported.")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise CatalogDataError("The XML document is not valid.") from exc
    if root.tag == "book":
        book_elements = [root]
    elif root.tag in {"books", "catalog"}:
        book_elements = list(root.findall("./book"))
    else:
        raise CatalogDataError("XML must contain a books or catalog root element.")
    if not book_elements and len(root) > 0:
        raise CatalogDataError("XML does not contain any book records.")
    records: list[dict[str, Any]] = []
    for index, book_element in enumerate(book_elements, start=1):
        record: dict[str, Any] = {}
        for child in book_element:
            if child.tag in BOOK_FIELDS:
                record[child.tag] = (
                    None if child.get("null") == "true" else (child.text or "")
                )
                if child.tag in INTEGER_FIELDS:
                    record[child.tag] = _csv_value(child.tag, record[child.tag])
        records.append(record)
    return records


def parse_catalog(data: bytes, format: CatalogFormat) -> list[dict[str, Any]]:
    """Parse the complete input before any database work occurs."""

    if not data:
        raise CatalogDataError("The catalog file is empty.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CatalogDataError("Catalog files must use UTF-8 encoding.") from exc
    if not text.strip():
        raise CatalogDataError("The catalog file is empty.")
    if format is CatalogFormat.JSON:
        return _parse_json(text)
    if format is CatalogFormat.CSV:
        return _parse_csv(text)
    return _parse_xml(text)


def _issue_from_validation(record_number: int, exc: ValidationError) -> ImportIssue:
    fields = sorted(
        {
            str(error["loc"][0])
            for error in exc.errors()
            if error.get("loc")
        }
    )
    messages = "; ".join(str(error.get("msg", "Invalid value.")) for error in exc.errors())
    return ImportIssue(record=record_number, message=messages, fields=fields)


def _normalise_identity(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None


def _positive_id(value: Any, record_number: int) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CatalogDataError("id must be a positive integer.", record=record_number) from exc
    if parsed <= 0:
        raise CatalogDataError("id must be a positive integer.", record=record_number)
    return parsed


def _lookup_existing(
    db: Session,
    record: dict[str, Any],
    record_number: int,
) -> Book | None:
    book_id = _positive_id(record.get("id"), record_number)
    existing = db.get(Book, book_id) if book_id is not None else None
    if existing is None:
        isbn = _normalise_identity(record.get("isbn"))
        if isbn is not None:
            existing = db.scalar(select(Book).where(Book.isbn == isbn))
    if existing is None:
        slug = _normalise_identity(record.get("slug"))
        if slug is not None:
            existing = db.scalar(select(Book).where(Book.slug == slug).order_by(Book.id))
    return existing


def _validate_and_plan(
    db: Session,
    records: list[dict[str, Any]],
) -> tuple[list[_ImportPlan], list[ImportIssue]]:
    plans: list[_ImportPlan] = []
    issues: list[ImportIssue] = []
    seen_keys: set[tuple[str, Any]] = set()

    for record_number, record in enumerate(records, start=1):
        unknown_fields = set(record) - set(BOOK_FIELDS)
        if unknown_fields:
            issues.append(
                ImportIssue(
                    record=record_number,
                    message="Unknown fields: " + ", ".join(sorted(unknown_fields)) + ".",
                    fields=sorted(unknown_fields),
                )
            )
            continue

        try:
            existing = _lookup_existing(db, record, record_number)
            if existing is not None:
                payload = BookUpdate.model_validate(
                    {key: value for key, value in record.items() if key in WRITABLE_FIELDS}
                )
            else:
                payload = BookCreate.model_validate(
                    {key: value for key, value in record.items() if key in WRITABLE_FIELDS}
                )
        except CatalogDataError as exc:
            issues.append(ImportIssue(record=record_number, message=exc.message))
            continue
        except ValidationError as exc:
            issues.append(_issue_from_validation(record_number, exc))
            continue

        identity = (
            ("id", existing.id)
            if existing is not None
            else (
                ("isbn", payload.isbn)
                if payload.isbn is not None
                else (("slug", payload.slug) if payload.slug is not None else None)
            )
        )
        if identity is not None:
            if identity in seen_keys:
                issues.append(
                    ImportIssue(
                        record=record_number,
                        message="The same catalog identity appears more than once in this import.",
                    )
                )
                continue
            seen_keys.add(identity)

        if existing is not None:
            if payload.isbn is not None:
                duplicate = db.scalar(
                    select(Book).where(Book.isbn == payload.isbn, Book.id != existing.id)
                )
                if duplicate is not None:
                    issues.append(
                        ImportIssue(
                            record=record_number,
                            message="ISBN is already used by another catalog record.",
                            fields=["isbn"],
                        )
                    )
                    continue
            if payload.total_copies is not None:
                borrowed = existing.total_copies - existing.available_copies
                if payload.total_copies < borrowed:
                    issues.append(
                        ImportIssue(
                            record=record_number,
                            message="Total copies cannot be lower than borrowed copies.",
                            fields=["total_copies"],
                        )
                    )
                    continue

        plans.append(
            _ImportPlan(
                record_number=record_number,
                payload=payload,
                existing=existing,
            )
        )
    return plans, issues


def apply_import(
    db: Session,
    records: list[dict[str, Any]],
) -> tuple[int, int]:
    """Validate every row, then apply all changes in one database transaction."""

    with db.begin():
        plans, issues = _validate_and_plan(db, records)
        if issues:
            raise CatalogDataError("One or more catalog records failed validation.") from None

        inserted = 0
        updated = 0
        try:
            for plan in plans:
                if plan.existing is None:
                    create_book(db, plan.payload, commit=False)  # type: ignore[arg-type]
                    inserted += 1
                else:
                    update_book(
                        db,
                        plan.existing,
                        plan.payload,  # type: ignore[arg-type]
                        commit=False,
                    )
                    updated += 1
        except BookInventoryConflict as exc:
            raise CatalogDataConflict(
                "An import record would discard borrowed inventory.",
                record=plan.record_number,
            ) from exc
        except IntegrityError as exc:
            raise CatalogDataConflict(
                "An import record conflicts with an existing catalog value.",
                record=plan.record_number,
            ) from exc
    return inserted, updated


def validate_and_apply_import(
    db: Session,
    records: list[dict[str, Any]],
) -> tuple[int, int, list[ImportIssue]]:
    """Return counts on success and validation issues without partial writes."""

    try:
        inserted, updated = apply_import(db, records)
    except CatalogDataError:
        # Re-run only the read-only planner after rollback so callers can show
        # record-level issues while the database remains unchanged.
        db.rollback()
        with db.begin():
            _, issues = _validate_and_plan(db, records)
        return 0, 0, issues or [ImportIssue(message="One or more records failed validation.")]
    except CatalogDataConflict as exc:
        db.rollback()
        return 0, 0, [ImportIssue(record=exc.record, message=exc.message)]
    return inserted, updated, []
