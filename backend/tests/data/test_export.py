"""CSV/JSON/XML catalog export and role-boundary contracts."""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET

import pytest

from .conftest import EXPORT_ENDPOINT


EXPORT_FORMATS = ("csv", "json", "xml")


def _book_records(response, file_format: str) -> list[dict]:
    if file_format == "csv":
        text = response.content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    if file_format == "json":
        payload = response.json()
        if isinstance(payload, list):
            records = payload
        else:
            records = payload.get("items") or payload.get("books") or payload.get("data")
        assert isinstance(records, list), payload
        return records

    root = ET.fromstring(response.content)
    elements = root.findall(".//book")
    return [
        {child.tag: child.text for child in element}
        for element in elements
    ]


@pytest.mark.parametrize("file_format", EXPORT_FORMATS)
def test_librarian_export_is_parseable_in_every_required_format(
    role_client,
    create_data_book,
    data_marker,
    file_format: str,
) -> None:
    client = role_client("LIBRARIAN")
    book = create_data_book(marker=data_marker)

    response = client.get(EXPORT_ENDPOINT, params={"format": file_format})

    assert response.status_code == 200, response.text
    expected_content_type = {
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
    }[file_format]
    assert response.headers["content-type"].split(";", 1)[0] == expected_content_type

    records = _book_records(response, file_format)
    matching = [record for record in records if record.get("title") == book.title]
    assert matching, records
    assert str(matching[0]["total_copies"]) == str(book.total_copies)


@pytest.mark.parametrize("role", ("LIBRARIAN", "ADMIN"))
def test_librarian_and_admin_can_export_all_formats(
    role_client,
    create_data_book,
    data_marker,
    role: str,
) -> None:
    client = role_client(role)
    create_data_book(marker=data_marker)

    for file_format in EXPORT_FORMATS:
        response = client.get(EXPORT_ENDPOINT, params={"format": file_format})
        assert response.status_code == 200, response.text
        assert _book_records(response, file_format)


@pytest.mark.parametrize("file_format", EXPORT_FORMATS)
def test_member_is_denied_catalog_export(
    role_client,
    file_format: str,
) -> None:
    client = role_client("MEMBER")

    response = client.get(EXPORT_ENDPOINT, params={"format": file_format})

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"
