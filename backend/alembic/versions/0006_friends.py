"""Create canonical unordered friendships."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_friends"
down_revision = "0005_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_low_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "user_high_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_friendships_pair"),
        sa.CheckConstraint(
            "user_low_id < user_high_id",
            name="ck_friendships_low_before_high",
        ),
    )
    op.create_index("ix_friendships_low_id", "friendships", ["user_low_id"])
    op.create_index("ix_friendships_high_id", "friendships", ["user_high_id"])


def downgrade() -> None:
    op.drop_index("ix_friendships_high_id", table_name="friendships")
    op.drop_index("ix_friendships_low_id", table_name="friendships")
    op.drop_table("friendships")
