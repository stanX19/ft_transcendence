"""File asset model and storage boundary contracts."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from .conftest import png_bytes


def test_file_asset_model_is_registered_with_safe_relationship_shape() -> None:
    from app.core.model_registry import Base
    from app.features.files.models import FileAsset

    assert FileAsset.__table__ is Base.metadata.tables["file_assets"]
    columns = inspect(FileAsset.__table__).columns
    assert {
        "id",
        "owner_user_id",
        "book_id",
        "kind",
        "original_filename",
        "stored_filename",
        "mime_type",
        "size_bytes",
        "created_at",
    }.issubset(columns.keys())
    assert columns["owner_user_id"].nullable is True
    assert columns["book_id"].nullable is True


def test_avatar_upload_uses_server_filename_and_id_file_endpoint(
    client,
    register_user,
    db_session,
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.core.config import get_settings
    from app.features.files.models import FileAsset
    from app.features.files.service import current_avatar

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    registration = register_user(client, display_name="Storage Avatar User")
    assert registration.status_code == 201, registration.text
    original_name = "../../not-a-safe-path.png"

    response = client.post(
        "/api/users/me/avatar",
        files={"file": (original_name, png_bytes(), "image/png")},
    )

    assert response.status_code == 201, response.text
    asset = response.json()["file"]
    assert asset["original_filename"] == original_name
    assert asset["stored_filename"] != original_name
    stored_path = tmp_path / asset["stored_filename"]
    assert stored_path.is_file()
    assert Path(asset["stored_filename"]).name == asset["stored_filename"]
    fetched = client.get(f"/api/files/{asset['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.content == png_bytes()
    assert current_avatar(db_session, registration.json()["user"]["id"]) is not None
    assert db_session.query(FileAsset).count() >= 1


def test_invalid_avatar_content_is_rejected(client, register_user) -> None:
    registration = register_user(client, display_name="Invalid Avatar User")
    assert registration.status_code == 201, registration.text

    response = client.post(
        "/api/users/me/avatar",
        files={"file": ("avatar.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"
