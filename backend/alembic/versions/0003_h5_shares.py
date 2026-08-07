"""Add server-side H5 share snapshots and recipient replies.

Revision ID: 0003_h5_shares
Revises: 0002_ai_assistant_threads
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_h5_shares"
down_revision = "0002_ai_assistant_threads"
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
        "h5_shares",
        _uuid_primary_key(),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=True),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("slug", name="uq_h5_shares_slug"),
    )
    op.create_index("ix_h5_shares_slug", "h5_shares", ["slug"])
    op.create_index("ix_h5_shares_plan_id", "h5_shares", ["plan_id"])
    op.create_index("ix_h5_shares_deleted_at", "h5_shares", ["deleted_at"])

    op.create_table(
        "h5_share_replies",
        _uuid_primary_key(),
        sa.Column("share_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reaction", sa.String(length=32), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["share_id"], ["h5_shares.id"], ondelete="CASCADE"),
        sa.CheckConstraint("length(content) BETWEEN 1 AND 300", name="ck_h5_share_reply_content_length"),
        sa.CheckConstraint(
            "reaction IS NULL OR length(reaction) BETWEEN 1 AND 32",
            name="ck_h5_share_reply_reaction_length",
        ),
    )
    op.create_index("ix_h5_share_replies_share_id", "h5_share_replies", ["share_id"])
    op.create_index("ix_h5_share_replies_share_created", "h5_share_replies", ["share_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_h5_share_replies_share_created", table_name="h5_share_replies")
    op.drop_index("ix_h5_share_replies_share_id", table_name="h5_share_replies")
    op.drop_table("h5_share_replies")
    op.drop_index("ix_h5_shares_deleted_at", table_name="h5_shares")
    op.drop_index("ix_h5_shares_plan_id", table_name="h5_shares")
    op.drop_index("ix_h5_shares_slug", table_name="h5_shares")
    op.drop_table("h5_shares")
