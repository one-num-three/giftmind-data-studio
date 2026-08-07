"""Server-side gift experience shares and recipient replies."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Share(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An immutable snapshot of a plan plus the giver's presentation config."""

    __tablename__ = "h5_shares"

    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    plan_id: Mapped[str | None] = mapped_column(String(128), index=True)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ShareReply(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A recipient's lightweight reply to a share; reactions reserved for later."""

    __tablename__ = "h5_share_replies"

    share_id: Mapped[str] = mapped_column(
        ForeignKey("h5_shares.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reaction: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        CheckConstraint("length(content) BETWEEN 1 AND 300", name="ck_h5_share_reply_content_length"),
        CheckConstraint(
            "reaction IS NULL OR length(reaction) BETWEEN 1 AND 32",
            name="ck_h5_share_reply_reaction_length",
        ),
        Index("ix_h5_share_replies_share_created", "share_id", "created_at"),
    )
