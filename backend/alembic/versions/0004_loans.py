"""Create the loans table and active-loan uniqueness index."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_loans"
down_revision = "0003_books"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.Integer(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column(
            "borrowed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "due_at >= borrowed_at",
            name="ck_loans_due_after_borrowed",
        ),
    )
    op.create_index(
        "uq_loans_active_user_book",
        "loans",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )
    op.create_index("ix_loans_user_id", "loans", ["user_id"])
    op.create_index("ix_loans_book_id", "loans", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_loans_book_id", table_name="loans")
    op.drop_index("ix_loans_user_id", table_name="loans")
    op.drop_index("uq_loans_active_user_book", table_name="loans")
    op.drop_table("loans")
