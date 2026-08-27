"""Avatar replacement and deletion contracts."""

from __future__ import annotations

from pathlib import Path

from .conftest import jpeg_bytes, png_bytes


def test_replacing_and_deleting_avatar_removes_old_metadata_and_bytes(
    client,
    register_user,
    db_session,
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.core.config import get_settings
    from app.features.files.models import FileAsset, FileKind

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    registration = register_user(client, display_name="Avatar Replacement User")
    assert registration.status_code == 201, registration.text

    first = client.post(
        "/api/users/me/avatar",
        files={"file": ("first.png", png_bytes(), "image/png")},
    )
    assert first.status_code == 201, first.text
    first_asset = first.json()["file"]
    first_path = tmp_path / first_asset["stored_filename"]
    assert first_path.exists()

    second = client.post(
        "/api/users/me/avatar",
        files={"file": ("second.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert second.status_code == 201, second.text
    second_asset = second.json()["file"]
    assert not first_path.exists()
    assets = db_session.query(FileAsset).filter(
        FileAsset.kind == FileKind.AVATAR,
        FileAsset.owner_user_id == registration.json()["user"]["id"],
    ).all()
    assert len(assets) == 1
    assert assets[0].id == second_asset["id"]

    deleted = client.delete("/api/users/me/avatar")
    assert deleted.status_code in (200, 204), deleted.text
    assert not (tmp_path / second_asset["stored_filename"]).exists()
    assert db_session.query(FileAsset).filter(FileAsset.id == second_asset["id"]).count() == 0
