"""Book cover/document upload, access, replacement, and authorization contracts."""

from __future__ import annotations

from pathlib import Path

from .conftest import jpeg_bytes, pdf_bytes


def test_member_cannot_manage_book_files(
    client,
    register_user,
    create_file_book,
) -> None:
    registration = register_user(client, display_name="Book File Member")
    assert registration.status_code == 201, registration.text
    book = create_file_book()

    response = client.post(
        f"/api/books/{book.id}/files",
        data={"kind": "BOOK_COVER"},
        files={"file": ("cover.jpg", jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 403, response.text


def test_librarian_can_replace_cover_upload_pdf_and_delete_asset(
    privileged_file_client,
    client_factory,
    create_file_book,
    db_session,
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.core.config import get_settings
    from app.features.files.models import FileAsset, FileKind

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = privileged_file_client("LIBRARIAN")
    book = create_file_book()

    first = client.post(
        f"/api/books/{book.id}/files",
        data={"kind": "BOOK_COVER"},
        files={"file": ("cover-one.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert first.status_code == 201, first.text
    first_asset = first.json()["file"]
    first_path = tmp_path / first_asset["stored_filename"]

    replacement = client.post(
        f"/api/books/{book.id}/files",
        data={"kind": "BOOK_COVER"},
        files={"file": ("cover-two.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert replacement.status_code == 201, replacement.text
    replacement_asset = replacement.json()["file"]
    assert not first_path.exists()
    assert db_session.query(FileAsset).filter(
        FileAsset.book_id == book.id,
        FileAsset.kind == FileKind.BOOK_COVER,
    ).count() == 1

    document = client.post(
        f"/api/books/{book.id}/files",
        data={"kind": "BOOK_DOCUMENT"},
        files={"file": ("sample.pdf", pdf_bytes(), "application/pdf")},
    )
    assert document.status_code == 201, document.text
    document_asset = document.json()["file"]
    assert client.get(f"/api/files/{document_asset['id']}").status_code == 200
    assert client_factory().get(f"/api/files/{document_asset['id']}").status_code == 401

    deleted = client.delete(f"/api/files/{replacement_asset['id']}")
    assert deleted.status_code in (200, 204), deleted.text
    assert not (tmp_path / replacement_asset["stored_filename"]).exists()
