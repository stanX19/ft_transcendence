"""Multipart import parsing, validation reporting, and database updates."""

from __future__ import annotations

import json

import pytest

from .conftest import (
    IMPORT_ENDPOINT,
    book_by_isbn,
    book_record,
    summary_from,
    upload_records,
    validation_errors_from,
)


IMPORT_FORMATS = ("csv", "json", "xml")


@pytest.mark.parametrize("file_format", IMPORT_FORMATS)
def test_librarian_can_import_multiple_records_in_every_format(
    role_client,
    db_session,
    data_marker,
    file_format: str,
) -> None:
    client = role_client("LIBRARIAN")
    first = book_record(f"{data_marker}-first")
    second = book_record(f"{data_marker}-second")

    response = upload_records(client, [first, second], file_format)

    assert response.status_code == 200, response.text
    summary = summary_from(response.json())
    assert summary["inserted"] == 2
    assert summary["updated"] == 0
    assert summary["rejected"] == 0
    assert book_by_isbn(db_session, first["isbn"]) is not None
    assert book_by_isbn(db_session, second["isbn"]) is not None


@pytest.mark.parametrize("file_format", IMPORT_FORMATS)
def test_member_is_denied_multipart_import(
    role_client,
    data_marker,
    file_format: str,
) -> None:
    client = role_client("MEMBER")
    record = book_record(data_marker)

    response = upload_records(client, [record], file_format)

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("file_format", IMPORT_FORMATS)
def test_invalid_record_returns_clear_row_error_and_no_write(
    role_client,
    db_session,
    data_marker,
    file_format: str,
) -> None:
    client = role_client("LIBRARIAN")
    invalid = book_record(
        f"{data_marker}-invalid",
        total_copies=-1,
    )

    response = upload_records(client, [invalid], file_format)

    assert response.status_code == 422, response.text
    payload = response.json()
    summary = summary_from(payload)
    assert summary["inserted"] == 0
    assert summary["updated"] == 0
    assert summary["rejected"] == 1
    errors = validation_errors_from(payload)
    assert errors
    assert "total_copies" in json.dumps(errors).lower()
    assert book_by_isbn(db_session, invalid["isbn"]) is None


def test_import_updates_existing_book_and_returns_inserted_updated_rejected_counts(
    role_client,
    create_data_book,
    db_session,
    data_marker,
) -> None:
    client = role_client("ADMIN")
    existing_isbn = f"978{data_marker[-10:]}"
    existing = create_data_book(
        marker=f"{data_marker}-existing",
        isbn=existing_isbn,
        title=f"Before import {data_marker}",
        total_copies=2,
    )
    new_record = book_record(f"{data_marker}-new")
    updated_record = book_record(
        f"{data_marker}-updated",
        isbn=existing_isbn,
        title=f"After import {data_marker}",
        total_copies=7,
    )

    response = upload_records(
        client,
        [updated_record, new_record],
        "json",
    )

    assert response.status_code == 200, response.text
    summary = summary_from(response.json())
    assert summary["inserted"] == 1
    assert summary["updated"] == 1
    assert summary["rejected"] == 0

    db_session.expire_all()
    updated = book_by_isbn(db_session, existing_isbn)
    inserted = book_by_isbn(db_session, new_record["isbn"])
    assert updated is not None
    assert updated.id == existing.id
    assert updated.title == updated_record["title"]
    assert updated.total_copies == updated_record["total_copies"]
    assert updated.available_copies == updated_record["total_copies"]
    assert inserted is not None


def test_import_route_requires_multipart_file(role_client) -> None:
    client = role_client("LIBRARIAN")

    response = client.post(IMPORT_ENDPOINT)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"
