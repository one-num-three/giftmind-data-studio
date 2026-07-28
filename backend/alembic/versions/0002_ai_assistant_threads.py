"""Add persistent AI assistant conversations.

Revision ID: 0002_ai_assistant_threads
Revises: 0001_initial_schema
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_ai_assistant_threads"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _uuid_primary_key() -> sa.Column:
    return sa.Column("id", sa.String(length=36), nullable=False, primary_key=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ai_threads",
        _uuid_primary_key(),
        sa.Column("draft_id", sa.String(length=128), nullable=False),
        sa.Column("gift_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("draft_id", name="uq_ai_threads_draft_id"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_ai_thread_status"),
    )
    op.create_index("ix_ai_threads_draft_id", "ai_threads", ["draft_id"])
    op.create_index("ix_ai_threads_gift_id", "ai_threads", ["gift_id"])

    op.create_table(
        "ai_messages",
        _uuid_primary_key(),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=False),
        sa.Column("source_refs_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["ai_threads.id"], ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_message_role"),
    )
    op.create_index("ix_ai_messages_thread_id", "ai_messages", ["thread_id"])

    op.create_table(
        "ai_suggestion_runs",
        _uuid_primary_key(),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("assistant_message_id", sa.String(length=36), nullable=False),
        sa.Column("patch_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_refs_json", sa.JSON(), nullable=False),
        sa.Column("applied_fields", sa.JSON(), nullable=False),
        sa.Column("ignored_fields", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["thread_id"], ["ai_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assistant_message_id"], ["ai_messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("assistant_message_id", name="uq_ai_suggestion_runs_message"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_ai_suggestion_confidence"),
        sa.CheckConstraint("source IN ('deepseek', 'rule')", name="ck_ai_suggestion_source"),
    )
    op.create_index("ix_ai_suggestion_runs_thread_id", "ai_suggestion_runs", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_suggestion_runs_thread_id", table_name="ai_suggestion_runs")
    op.drop_table("ai_suggestion_runs")
    op.drop_index("ix_ai_messages_thread_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_threads_gift_id", table_name="ai_threads")
    op.drop_index("ix_ai_threads_draft_id", table_name="ai_threads")
    op.drop_table("ai_threads")
