"""SQLAlchemy engine, declarative base, and request session lifecycle."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


def get_database_url(settings: Settings | None = None) -> str:
    """Select the isolated database URL when the application is in test mode."""

    active_settings = settings or get_settings()
    if active_settings.app_env == "test":
        return active_settings.test_database_url
    return active_settings.database_url


class Base(DeclarativeBase):
    """Base class shared by all SQLAlchemy models."""


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one session per request and always close it afterward."""

    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
