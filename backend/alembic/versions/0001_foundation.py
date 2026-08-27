"""Create the initial migration checkpoint.

Feature slices own their tables and will add revisions after foundation. An
empty first revision still makes startup migration-controlled and gives a
stable Alembic head for clean databases.
"""

from __future__ import annotations


revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
