"""Controlled custom-field definitions and persisted JSON values."""

from sqlalchemy import Boolean, CheckConstraint, DDL, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CustomFieldDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "custom_field_definitions"

    machine_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(16), default="single", nullable=False)
    required_mode: Mapped[str] = mapped_column(String(32), default="never", nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64))
    decimal_places: Mapped[int | None] = mapped_column(Integer)
    help_text: Mapped[str | None] = mapped_column(Text)
    example_valid: Mapped[str | None] = mapped_column(Text)
    example_invalid: Mapped[str | None] = mapped_column(Text)
    default_value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    validation_json: Mapped[dict | list | None] = mapped_column(JSON)
    conflict_rules_json: Mapped[dict | list | None] = mapped_column(JSON)
    source_requirement: Mapped[str | None] = mapped_column(String(64))
    ai_policy: Mapped[str] = mapped_column(String(32), default="suggest", nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sortable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completeness_weight: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    export_mapping_json: Mapped[dict | list | None] = mapped_column(JSON)
    introduced_version: Mapped[int] = mapped_column(Integer, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    replacement_field_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("custom_field_definitions.id", ondelete="RESTRICT")
    )

    __table_args__ = (
        CheckConstraint("machine_key GLOB '[a-z]*' AND machine_key NOT GLOB '*[^a-z0-9_]*'", name="ck_custom_field_machine_key"),
        CheckConstraint("cardinality IN ('single', 'multiple')", name="ck_custom_field_cardinality"),
        CheckConstraint("required_mode IN ('never', 'draft_optional', 'complete_required')", name="ck_custom_field_required_mode"),
        CheckConstraint("ai_policy IN ('prohibited', 'suggest', 'infer_with_confirmation')", name="ck_custom_field_ai_policy"),
        CheckConstraint("state IN ('draft', 'active', 'deprecated', 'retired')", name="ck_custom_field_state"),
        CheckConstraint("introduced_version >= 1", name="ck_custom_field_introduced_version"),
        CheckConstraint("decimal_places IS NULL OR decimal_places >= 0", name="ck_custom_field_decimal_places"),
        CheckConstraint("completeness_weight >= 0", name="ck_custom_field_completeness_weight"),
    )


class GiftCustomFieldValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gift_custom_field_values"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False)
    field_definition_id: Mapped[str] = mapped_column(
        ForeignKey("custom_field_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("gift_id", "field_definition_id", name="uq_gift_custom_field_value"),
    )


machine_key_immutable_trigger = DDL(
    """
    CREATE TRIGGER custom_field_machine_key_immutable
    BEFORE UPDATE OF machine_key ON custom_field_definitions
    FOR EACH ROW WHEN EXISTS (
        SELECT 1 FROM gift_custom_field_values WHERE field_definition_id = OLD.id
    )
    BEGIN
        SELECT RAISE(ABORT, 'machine_key is immutable after first value');
    END
    """
).execute_if(dialect="sqlite")
event.listen(CustomFieldDefinition.__table__, "after_create", machine_key_immutable_trigger)
