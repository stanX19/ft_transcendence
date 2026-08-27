"""Single Alembic import point for SQLAlchemy model discovery.

Feature model modules should be imported here as they are added. Keeping
those imports in one intentionally boring registry ensures Alembic sees the
complete ``Base.metadata`` without spreading migration-only imports through
the application.
"""

from app.core.database import Base

__all__ = ["Base"]
