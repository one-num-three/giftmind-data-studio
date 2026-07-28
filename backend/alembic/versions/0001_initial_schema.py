"""Create the locked version-1 GiftMind product/activity contract.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-27
"""

from datetime import UTC, datetime

from alembic import op

from backend.app.models import GiftTypeDefinition
from backend.app.models.base import Base


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the complete version-1 table set and fixed top-level types."""
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=False)
    now = datetime.now(UTC)
    op.bulk_insert(
        GiftTypeDefinition.__table__,
        [
            {"code": "product", "name": "商品", "status": "active", "contract_version": 1, "created_at": now, "updated_at": now},
            {"code": "activity", "name": "活动", "status": "active", "contract_version": 1, "created_at": now, "updated_at": now},
        ],
    )


def downgrade() -> None:
    """Remove the initial contract in dependency-safe reverse order."""
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=False)
