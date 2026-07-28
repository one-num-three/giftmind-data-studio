"""Top-level gift types and configurable dimension values."""

from sqlalchemy import CheckConstraint, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GiftTypeDefinition(Base, TimestampMixin):
    __tablename__ = "gift_type_definitions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'deprecated', 'retired')", name="ck_gift_type_state"),
        CheckConstraint("contract_version >= 1", name="ck_gift_type_contract_version"),
    )


class DimensionOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dimension_options"

    dimension_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(64), default="common", nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("state IN ('draft', 'active', 'deprecated', 'retired')", name="ck_dimension_option_state"),
        CheckConstraint("display_order >= 0", name="ck_dimension_option_display_order"),
        {"sqlite_autoincrement": False},
    )
