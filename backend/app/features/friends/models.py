"""Canonical unordered friendship model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Friendship(Base):
    """One friendship stored with the lower user id first."""

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("user_low_id", "user_high_id", name="uq_friendships_pair"),
        CheckConstraint(
            "user_low_id < user_high_id",
            name="ck_friendships_low_before_high",
        ),
        Index("ix_friendships_low_id", "user_low_id"),
        Index("ix_friendships_high_id", "user_high_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_low_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    user_high_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
