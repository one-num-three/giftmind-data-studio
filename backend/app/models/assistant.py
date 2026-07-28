"""Persistent, per-gift AI assistant conversations and review state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class AIThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_threads"

    draft_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    gift_id: Mapped[str | None] = mapped_column(
        ForeignKey("gifts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_ai_thread_status"),
    )


class AIMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ai_messages"

    thread_id: Mapped[str] = mapped_column(
        ForeignKey("ai_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_refs_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_message_role"),
    )


class AISuggestionRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_suggestion_runs"

    thread_id: Mapped[str] = mapped_column(
        ForeignKey("ai_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assistant_message_id: Mapped[str] = mapped_column(
        ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    patch_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="rule", nullable=False)
    source_refs_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    applied_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    ignored_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_ai_suggestion_confidence"),
        CheckConstraint("source IN ('deepseek', 'rule')", name="ck_ai_suggestion_source"),
    )
