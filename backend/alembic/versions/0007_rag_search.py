"""Add the PostgreSQL full-text catalog search document."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_rag_search"
down_revision = "0006_friends"
branch_labels = None
depends_on = None


_SEARCH_EXPRESSION = (
    "to_tsvector('simple', "
    "coalesce(title, '') || ' ' || "
    "coalesce(author, '') || ' ' || "
    "coalesce(description, '') || ' ' || "
    "coalesce(category, ''))"
)


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column(
            "search_document",
            postgresql.TSVECTOR(),
            sa.Computed(_SEARCH_EXPRESSION, persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_books_search_document",
        "books",
        ["search_document"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_books_search_document", table_name="books")
    op.drop_column("books", "search_document")
