"""Create users, account profiles, roles, and presence timestamps."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_users"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    role_enum = postgresql.ENUM(
        "MEMBER",
        "LIBRARIAN",
        "ADMIN",
        name="user_role",
    )
    role_enum.create(bind, checkfirst=True)
    role_column_enum = postgresql.ENUM(
        "MEMBER",
        "LIBRARIAN",
        "ADMIN",
        name="user_role",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "role",
            role_column_enum,
            nullable=False,
            server_default=sa.text("'MEMBER'"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("users")
    postgresql.ENUM(
        "MEMBER",
        "LIBRARIAN",
        "ADMIN",
        name="user_role",
    ).drop(bind, checkfirst=True)
