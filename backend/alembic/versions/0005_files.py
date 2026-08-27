"""Create file metadata and its safe ownership constraints."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_files"
down_revision = "0004_loans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "book_id",
            sa.Integer(),
            sa.ForeignKey("books.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "((owner_user_id IS NOT NULL AND book_id IS NULL) OR "
            "(owner_user_id IS NULL AND book_id IS NOT NULL))",
            name="ck_file_assets_single_owner",
        ),
        sa.CheckConstraint(
            "kind IN ('AVATAR', 'BOOK_COVER', 'BOOK_DOCUMENT')",
            name="ck_file_assets_kind",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_file_assets_size_nonnegative"),
        sa.UniqueConstraint("stored_filename", name="uq_file_assets_stored_filename"),
    )
    op.create_index(
        "uq_file_assets_current_avatar",
        "file_assets",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NOT NULL AND kind = 'AVATAR'"),
    )
    op.create_index(
        "uq_file_assets_current_cover",
        "file_assets",
        ["book_id"],
        unique=True,
        postgresql_where=sa.text("book_id IS NOT NULL AND kind = 'BOOK_COVER'"),
    )
    op.create_index("ix_file_assets_owner_user_id", "file_assets", ["owner_user_id"])
    op.create_index("ix_file_assets_book_id", "file_assets", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_file_assets_book_id", table_name="file_assets")
    op.drop_index("ix_file_assets_owner_user_id", table_name="file_assets")
    op.drop_index("uq_file_assets_current_cover", table_name="file_assets")
    op.drop_index("uq_file_assets_current_avatar", table_name="file_assets")
    op.drop_table("file_assets")
