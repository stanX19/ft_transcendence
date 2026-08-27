"""Database metadata for user avatars and catalog file assets."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FileKind(str, Enum):
    """Supported file purposes and their ownership boundary."""

    AVATAR = "AVATAR"
    BOOK_COVER = "BOOK_COVER"
    BOOK_DOCUMENT = "BOOK_DOCUMENT"


class FileAsset(Base):
    """Metadata for one server-named file stored in the uploads volume."""

    __tablename__ = "file_assets"
    __table_args__ = (
        CheckConstraint(
            "((owner_user_id IS NOT NULL AND book_id IS NULL) OR "
            "(owner_user_id IS NULL AND book_id IS NOT NULL))",
            name="ck_file_assets_single_owner",
        ),
        CheckConstraint(
            "kind IN ('AVATAR', 'BOOK_COVER', 'BOOK_DOCUMENT')",
            name="ck_file_assets_kind",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_file_assets_size_nonnegative"),
        Index(
            "uq_file_assets_current_avatar",
            "owner_user_id",
            unique=True,
            postgresql_where=text("owner_user_id IS NOT NULL AND kind = 'AVATAR'"),
        ),
        Index(
            "uq_file_assets_current_cover",
            "book_id",
            unique=True,
            postgresql_where=text("book_id IS NOT NULL AND kind = 'BOOK_COVER'"),
        ),
        Index("ix_file_assets_owner_user_id", "owner_user_id"),
        Index("ix_file_assets_book_id", "book_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    book_id: Mapped[int | None] = mapped_column(
        ForeignKey("books.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
