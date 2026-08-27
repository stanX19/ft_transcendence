"""Atomicity contracts for catalog bulk imports."""

from __future__ import annotations

import pytest

from .conftest import (
    IMPORT_ENDPOINT,
    book_by_isbn,
    book_record,
    summary_from,
    upload_records,
    validation_errors_from,
)


@pytest.mark.parametrize("file_format", ("csv", "json", "xml"))
def test_mixed_valid_invalid_batch_is_atomic(
    role_client,
    db_session,
    data_marker,
    file_format: str,
) -> None:
    client = role_client("LIBRARIAN")
    valid = book_record(f"{data_marker}-valid")
    invalid = book_record(
        f"{data_marker}-invalid",
        total_copies=-1,
    )

    response = upload_records(client, [valid, invalid], file_format)

    assert response.status_code == 422, response.text
    payload = response.json()
    summary = summary_from(payload)
    assert summary["inserted"] == 0
    assert summary["updated"] == 0
    assert summary["rejected"] == 1
    assert validation_errors_from(payload)
    assert book_by_isbn(db_session, valid["isbn"]) is None
    assert book_by_isbn(db_session, invalid["isbn"]) is None


def test_malformed_json_is_fatal_without_partial_database_writes(
    role_client,
    db_session,
    data_marker,
) -> None:
    client = role_client("ADMIN")
    valid = book_record(f"{data_marker}-valid")
    malformed = (
        "[{\"isbn\": "
        + repr(valid["isbn"])
        + ", \"title\": \"unterminated\""
    ).encode("utf-8")

    response = client.post(
        IMPORT_ENDPOINT,
        files={
            "file": (
                "malformed.json",
                malformed,
                "application/json",
            )
        },
    )

    assert response.status_code in (400, 422), response.text
    payload = response.json()
    summary = summary_from(payload)
    assert summary["inserted"] == 0
    assert summary["updated"] == 0
    assert summary["rejected"] == 1
    assert validation_errors_from(payload)
    assert book_by_isbn(db_session, valid["isbn"]) is None
