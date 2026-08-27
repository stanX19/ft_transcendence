"""Create the catalog books table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_books"
down_revision = "0002_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("isbn", sa.String(length=32), nullable=True),
        sa.Column(
            "slug",
            sa.String(length=200),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("total_copies", sa.Integer(), nullable=False),
        sa.Column("available_copies", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("isbn", name="uq_books_isbn"),
        sa.CheckConstraint(
            "total_copies >= 0",
            name="ck_books_total_copies_nonnegative",
        ),
        sa.CheckConstraint(
            "available_copies >= 0",
            name="ck_books_available_copies_nonnegative",
        ),
        sa.CheckConstraint(
            "available_copies <= total_copies",
            name="ck_books_available_copies_lte_total",
        ),
    )
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_author", "books", ["author"])
    op.create_index("ix_books_category", "books", ["category"])


def downgrade() -> None:
    op.drop_index("ix_books_category", table_name="books")
    op.drop_index("ix_books_author", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
