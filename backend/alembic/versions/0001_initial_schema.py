"""Create the frozen version-1 GiftMind product/activity contract.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-27
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
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
    """Create the fixed V1 schema without importing live application metadata."""
    op.create_table(
        "gift_type_definitions",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('draft', 'active', 'deprecated', 'retired')", name="ck_gift_type_state"),
        sa.CheckConstraint("contract_version >= 1", name="ck_gift_type_contract_version"),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "dimension_options",
        _uuid_primary_key(),
        sa.Column("dimension_key", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("state IN ('draft', 'active', 'deprecated', 'retired')", name="ck_dimension_option_state"),
        sa.CheckConstraint("display_order >= 0", name="ck_dimension_option_display_order"),
    )
    op.create_table(
        "gifts",
        _uuid_primary_key(),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("gift_type_code", sa.String(length=64), nullable=False),
        sa.Column("canonical_name", sa.String(length=256), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("subcategory_code", sa.String(length=128), nullable=True),
        sa.Column("is_customizable", sa.Boolean(), nullable=False),
        sa.Column("is_bundle", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=True),
        sa.Column("completeness_score", sa.Integer(), nullable=True),
        sa.Column("recipient_types", sa.JSON(), nullable=False),
        sa.Column("relationship_stages", sa.JSON(), nullable=False),
        sa.Column("age_ranges", sa.JSON(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("occasions", sa.JSON(), nullable=False),
        sa.Column("desired_feelings", sa.JSON(), nullable=False),
        sa.Column("memory_hooks", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("custom_tags", sa.JSON(), nullable=False),
        sa.Column("price_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("price_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("lead_days_min", sa.Integer(), nullable=True),
        sa.Column("lead_days_max", sa.Integer(), nullable=True),
        sa.Column("rush_available", sa.Boolean(), nullable=False),
        sa.Column("taboo_flags", sa.JSON(), nullable=False),
        sa.Column("allergy_notes", sa.Text(), nullable=True),
        sa.Column("safety_notes", sa.Text(), nullable=True),
        sa.Column("unsuitable_groups", sa.JSON(), nullable=False),
        sa.Column("why_template", sa.Text(), nullable=True),
        sa.Column("best_scenarios", sa.Text(), nullable=True),
        sa.Column("unsuitable_scenarios", sa.Text(), nullable=True),
        sa.Column("purchase_or_booking_tip", sa.Text(), nullable=True),
        sa.Column("ritual_tip", sa.Text(), nullable=True),
        sa.Column("pairing_ideas", sa.Text(), nullable=True),
        sa.Column("collector_notes", sa.Text(), nullable=True),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("source_urls", sa.JSON(), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["gift_type_code"], ["gift_type_definitions.code"], ondelete="RESTRICT"),
        sa.CheckConstraint("schema_version >= 1", name="ck_gifts_schema_version"),
        sa.CheckConstraint("completeness_score IS NULL OR completeness_score BETWEEN 0 AND 100", name="ck_gifts_completeness_score"),
        sa.CheckConstraint("price_min IS NULL OR price_min >= 0", name="ck_gifts_price_min_nonnegative"),
        sa.CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_gifts_price_max_nonnegative"),
        sa.CheckConstraint("price_min IS NULL OR price_max IS NULL OR price_min <= price_max", name="ck_gifts_price_range"),
        sa.CheckConstraint("lead_days_min IS NULL OR lead_days_min >= 0", name="ck_gifts_lead_min_nonnegative"),
        sa.CheckConstraint("lead_days_max IS NULL OR lead_days_max >= 0", name="ck_gifts_lead_max_nonnegative"),
        sa.CheckConstraint("lead_days_min IS NULL OR lead_days_max IS NULL OR lead_days_min <= lead_days_max", name="ck_gifts_lead_range"),
    )
    op.create_table(
        "product_details",
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("product_form", sa.String(length=32), nullable=False),
        sa.Column("generic_product_name", sa.String(length=256), nullable=True),
        sa.Column("materials", sa.JSON(), nullable=False),
        sa.Column("colors", sa.JSON(), nullable=False),
        sa.Column("sizes", sa.JSON(), nullable=False),
        sa.Column("specifications", sa.JSON(), nullable=True),
        sa.Column("variant_notes", sa.Text(), nullable=True),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("package_dimensions", sa.String(length=128), nullable=True),
        sa.Column("size_class", sa.String(length=64), nullable=True),
        sa.Column("is_bulky", sa.Boolean(), nullable=False),
        sa.Column("is_fragile", sa.Boolean(), nullable=False),
        sa.Column("is_consumable", sa.Boolean(), nullable=False),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("storage_requirements", sa.Text(), nullable=True),
        sa.Column("personalization_methods", sa.JSON(), nullable=False),
        sa.Column("personalization_requirements", sa.Text(), nullable=True),
        sa.Column("device_or_platform_compatibility", sa.JSON(), nullable=False),
        sa.Column("digital_delivery_method", sa.String(length=128), nullable=True),
        sa.Column("shipping_required", sa.Boolean(), nullable=False),
        sa.Column("shipping_notes", sa.Text(), nullable=True),
        sa.Column("return_risk_notes", sa.Text(), nullable=True),
        sa.Column("warranty_expectation", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("gift_id"),
        sa.CheckConstraint("weight_grams IS NULL OR weight_grams >= 0", name="ck_product_weight_nonnegative"),
        sa.CheckConstraint("shelf_life_days IS NULL OR shelf_life_days >= 0", name="ck_product_shelf_life_nonnegative"),
    )
    op.create_table(
        "activity_details",
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("activity_mode", sa.String(length=32), nullable=False),
        sa.Column("activity_category", sa.String(length=128), nullable=True),
        sa.Column("service_regions", sa.JSON(), nullable=False),
        sa.Column("duration_minutes_min", sa.Integer(), nullable=True),
        sa.Column("duration_minutes_max", sa.Integer(), nullable=True),
        sa.Column("participants_min", sa.Integer(), nullable=True),
        sa.Column("participants_max", sa.Integer(), nullable=True),
        sa.Column("pricing_unit", sa.String(length=64), nullable=True),
        sa.Column("schedule_type", sa.String(length=64), nullable=True),
        sa.Column("booking_required", sa.Boolean(), nullable=False),
        sa.Column("booking_lead_days_min", sa.Integer(), nullable=True),
        sa.Column("booking_lead_days_max", sa.Integer(), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column("included_items", sa.JSON(), nullable=False),
        sa.Column("excluded_items", sa.JSON(), nullable=False),
        sa.Column("equipment_requirements", sa.Text(), nullable=True),
        sa.Column("age_restrictions", sa.Text(), nullable=True),
        sa.Column("height_restrictions", sa.Text(), nullable=True),
        sa.Column("health_restrictions", sa.Text(), nullable=True),
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
        sa.Column("weather_dependency", sa.String(length=64), nullable=True),
        sa.Column("indoor_outdoor", sa.String(length=64), nullable=True),
        sa.Column("cancellation_expectation", sa.Text(), nullable=True),
        sa.Column("reschedule_expectation", sa.Text(), nullable=True),
        sa.Column("refund_expectation", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("gift_id"),
        sa.CheckConstraint("duration_minutes_min IS NULL OR duration_minutes_min >= 0", name="ck_activity_duration_min_nonnegative"),
        sa.CheckConstraint("duration_minutes_max IS NULL OR duration_minutes_max >= 0", name="ck_activity_duration_max_nonnegative"),
        sa.CheckConstraint("duration_minutes_min IS NULL OR duration_minutes_max IS NULL OR duration_minutes_min <= duration_minutes_max", name="ck_activity_duration_range"),
        sa.CheckConstraint("participants_min IS NULL OR participants_min >= 0", name="ck_activity_participants_min_nonnegative"),
        sa.CheckConstraint("participants_max IS NULL OR participants_max >= 0", name="ck_activity_participants_max_nonnegative"),
        sa.CheckConstraint("participants_min IS NULL OR participants_max IS NULL OR participants_min <= participants_max", name="ck_activity_participants_range"),
        sa.CheckConstraint("booking_lead_days_min IS NULL OR booking_lead_days_min >= 0", name="ck_activity_booking_lead_min_nonnegative"),
        sa.CheckConstraint("booking_lead_days_max IS NULL OR booking_lead_days_max >= 0", name="ck_activity_booking_lead_max_nonnegative"),
        sa.CheckConstraint("booking_lead_days_min IS NULL OR booking_lead_days_max IS NULL OR booking_lead_days_min <= booking_lead_days_max", name="ck_activity_booking_lead_range"),
        sa.CheckConstraint("validity_days IS NULL OR validity_days >= 0", name="ck_activity_validity_nonnegative"),
    )
    op.create_table(
        "product_offers",
        _uuid_primary_key(),
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("merchant", sa.String(length=256), nullable=False),
        sa.Column("brand", sa.String(length=256), nullable=True),
        sa.Column("offer_name", sa.String(length=256), nullable=True),
        sa.Column("sku_or_model", sa.String(length=256), nullable=True),
        sa.Column("current_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("stock_status", sa.String(length=64), nullable=True),
        sa.Column("ship_from", sa.String(length=256), nullable=True),
        sa.Column("service_regions", sa.JSON(), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("purchase_url", sa.Text(), nullable=True),
        sa.Column("return_policy", sa.Text(), nullable=True),
        sa.Column("warranty_policy", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.CheckConstraint("current_price IS NULL OR current_price >= 0", name="ck_product_offer_price_nonnegative"),
        sa.CheckConstraint("delivery_days IS NULL OR delivery_days >= 0", name="ck_product_offer_delivery_nonnegative"),
        sa.CheckConstraint("shipping_cost IS NULL OR shipping_cost >= 0", name="ck_product_offer_shipping_nonnegative"),
    )
    op.create_table(
        "activity_offers",
        _uuid_primary_key(),
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=256), nullable=False),
        sa.Column("offer_name", sa.String(length=256), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("venue_name", sa.String(length=256), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("service_regions", sa.JSON(), nullable=False),
        sa.Column("current_price_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("current_price_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("pricing_unit", sa.String(length=64), nullable=True),
        sa.Column("opening_hours_or_schedule_notes", sa.Text(), nullable=True),
        sa.Column("availability_status", sa.String(length=64), nullable=True),
        sa.Column("booking_url", sa.Text(), nullable=True),
        sa.Column("booking_contact", sa.String(length=256), nullable=True),
        sa.Column("cancellation_policy", sa.Text(), nullable=True),
        sa.Column("reschedule_policy", sa.Text(), nullable=True),
        sa.Column("refund_policy", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.CheckConstraint("current_price_min IS NULL OR current_price_min >= 0", name="ck_activity_offer_price_min_nonnegative"),
        sa.CheckConstraint("current_price_max IS NULL OR current_price_max >= 0", name="ck_activity_offer_price_max_nonnegative"),
        sa.CheckConstraint("current_price_min IS NULL OR current_price_max IS NULL OR current_price_min <= current_price_max", name="ck_activity_offer_price_range"),
        sa.CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_activity_offer_longitude"),
        sa.CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_activity_offer_latitude"),
    )
    op.create_table(
        "gift_bundle_components",
        _uuid_primary_key(),
        sa.Column("bundle_gift_id", sa.String(length=36), nullable=False),
        sa.Column("component_gift_id", sa.String(length=36), nullable=False),
        sa.Column("component_type_code", sa.String(length=64), nullable=True),
        sa.Column("component_name", sa.String(length=256), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("role_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["bundle_gift_id"], ["gifts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["component_gift_id"], ["gifts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("bundle_gift_id <> component_gift_id", name="ck_bundle_component_not_self"),
        sa.CheckConstraint("quantity >= 1", name="ck_bundle_component_quantity"),
        sa.CheckConstraint("display_order >= 0", name="ck_bundle_component_display_order"),
    )
    op.create_table(
        "custom_field_definitions",
        _uuid_primary_key(),
        sa.Column("machine_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("cardinality", sa.String(length=16), nullable=False),
        sa.Column("required_mode", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=True),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("example_valid", sa.Text(), nullable=True),
        sa.Column("example_invalid", sa.Text(), nullable=True),
        sa.Column("default_value_json", sa.JSON(), nullable=True),
        sa.Column("validation_json", sa.JSON(), nullable=True),
        sa.Column("conflict_rules_json", sa.JSON(), nullable=True),
        sa.Column("source_requirement", sa.String(length=64), nullable=True),
        sa.Column("ai_policy", sa.String(length=32), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("is_searchable", sa.Boolean(), nullable=False),
        sa.Column("is_filterable", sa.Boolean(), nullable=False),
        sa.Column("is_sortable", sa.Boolean(), nullable=False),
        sa.Column("completeness_weight", sa.Integer(), nullable=False),
        sa.Column("export_mapping_json", sa.JSON(), nullable=True),
        sa.Column("introduced_version", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("replacement_field_definition_id", sa.String(length=36), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["replacement_field_definition_id"], ["custom_field_definitions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("machine_key", name="uq_custom_field_definitions_machine_key"),
        sa.CheckConstraint("machine_key GLOB '[a-z]*' AND machine_key NOT GLOB '*[^a-z0-9_]*'", name="ck_custom_field_machine_key"),
        sa.CheckConstraint("cardinality IN ('single', 'multiple')", name="ck_custom_field_cardinality"),
        sa.CheckConstraint("required_mode IN ('never', 'draft_optional', 'complete_required')", name="ck_custom_field_required_mode"),
        sa.CheckConstraint("ai_policy IN ('prohibited', 'suggest', 'infer_with_confirmation')", name="ck_custom_field_ai_policy"),
        sa.CheckConstraint("state IN ('draft', 'active', 'deprecated', 'retired')", name="ck_custom_field_state"),
        sa.CheckConstraint("introduced_version >= 1", name="ck_custom_field_introduced_version"),
        sa.CheckConstraint("decimal_places IS NULL OR decimal_places >= 0", name="ck_custom_field_decimal_places"),
        sa.CheckConstraint("completeness_weight >= 0", name="ck_custom_field_completeness_weight"),
    )
    op.create_table(
        "gift_custom_field_values",
        _uuid_primary_key(),
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("field_definition_id", sa.String(length=36), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["field_definition_id"], ["custom_field_definitions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("gift_id", "field_definition_id", name="uq_gift_custom_field_value"),
    )
    op.create_table(
        "gift_images",
        _uuid_primary_key(),
        sa.Column("gift_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stored_filename", name="uq_gift_images_stored_filename"),
        sa.CheckConstraint("width IS NULL OR width > 0", name="ck_gift_image_width"),
        sa.CheckConstraint("height IS NULL OR height > 0", name="ck_gift_image_height"),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_gift_image_size"),
        sa.CheckConstraint("display_order >= 0", name="ck_gift_image_display_order"),
    )
    op.create_table(
        "audit_events",
        _uuid_primary_key(),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ai_runs",
        _uuid_primary_key(),
        sa.Column("gift_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], ondelete="SET NULL"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_ai_run_duration"),
        sa.CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="ck_ai_run_input_tokens"),
        sa.CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="ck_ai_run_output_tokens"),
    )
    op.create_table(
        "import_runs",
        _uuid_primary_key(),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("import_format", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False),
        sa.Column("imported_records", sa.Integer(), nullable=False),
        sa.Column("rejected_records", sa.Integer(), nullable=False),
        sa.Column("error_report_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("total_records >= 0", name="ck_import_total_records"),
        sa.CheckConstraint("imported_records >= 0", name="ck_import_imported_records"),
        sa.CheckConstraint("rejected_records >= 0", name="ck_import_rejected_records"),
    )
    op.create_table(
        "backup_records",
        _uuid_primary_key(),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("backup_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("filename", name="uq_backup_records_filename"),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_backup_file_size"),
        sa.CheckConstraint("schema_version >= 1", name="ck_backup_schema_version"),
    )

    op.create_index("ix_dimension_options_dimension_key", "dimension_options", ["dimension_key"])
    op.create_index("ix_gifts_gift_type_code", "gifts", ["gift_type_code"])
    op.create_index("ix_gifts_canonical_name", "gifts", ["canonical_name"])
    op.create_index("ix_gifts_subcategory_code", "gifts", ["subcategory_code"])
    op.create_index("ix_gifts_deleted_at", "gifts", ["deleted_at"])
    op.create_index("ix_product_offers_gift_id", "product_offers", ["gift_id"])
    op.create_index("ix_activity_offers_gift_id", "activity_offers", ["gift_id"])
    op.create_index("ix_gift_bundle_components_bundle_gift_id", "gift_bundle_components", ["bundle_gift_id"])
    op.create_index("ix_gift_bundle_components_component_gift_id", "gift_bundle_components", ["component_gift_id"])
    op.create_index("ix_gift_images_gift_id", "gift_images", ["gift_id"])
    op.create_index("ix_gift_images_sha256", "gift_images", ["sha256"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_ai_runs_gift_id", "ai_runs", ["gift_id"])

    now = datetime.now(UTC)
    op.bulk_insert(
        sa.table(
            "gift_type_definitions",
            sa.column("code", sa.String()), sa.column("name", sa.String()), sa.column("status", sa.String()),
            sa.column("contract_version", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {"code": "product", "name": "商品", "status": "active", "contract_version": 1, "created_at": now, "updated_at": now},
            {"code": "activity", "name": "活动", "status": "active", "contract_version": 1, "created_at": now, "updated_at": now},
        ],
    )

    op.execute("""
        CREATE TRIGGER gift_type_active_v1_insert
        BEFORE INSERT ON gift_type_definitions
        WHEN NEW.status = 'active' AND NEW.code NOT IN ('product', 'activity')
        BEGIN SELECT RAISE(ABORT, 'only product and activity may be active in schema version 1'); END
    """)
    op.execute("""
        CREATE TRIGGER gift_type_active_v1_update
        BEFORE UPDATE OF code, status ON gift_type_definitions
        WHEN NEW.status = 'active' AND NEW.code NOT IN ('product', 'activity')
        BEGIN SELECT RAISE(ABORT, 'only product and activity may be active in schema version 1'); END
    """)
    op.execute("""
        CREATE TRIGGER gifts_require_active_type_insert
        BEFORE INSERT ON gifts
        WHEN NOT EXISTS (SELECT 1 FROM gift_type_definitions WHERE code = NEW.gift_type_code AND status = 'active')
        BEGIN SELECT RAISE(ABORT, 'gifts require an active type definition'); END
    """)
    op.execute("""
        CREATE TRIGGER gifts_require_active_type_update
        BEFORE UPDATE OF gift_type_code ON gifts
        WHEN NOT EXISTS (SELECT 1 FROM gift_type_definitions WHERE code = NEW.gift_type_code AND status = 'active')
          OR (NEW.gift_type_code <> 'product' AND EXISTS (SELECT 1 FROM product_details WHERE gift_id = NEW.id))
          OR (NEW.gift_type_code <> 'activity' AND EXISTS (SELECT 1 FROM activity_details WHERE gift_id = NEW.id))
        BEGIN SELECT RAISE(ABORT, 'gift type must be active and match existing details'); END
    """)
    op.execute("""
        CREATE TRIGGER product_details_require_product_insert
        BEFORE INSERT ON product_details
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'product')
          OR EXISTS (SELECT 1 FROM activity_details WHERE gift_id = NEW.gift_id)
        BEGIN SELECT RAISE(ABORT, 'product details require a product gift with no activity details'); END
    """)
    op.execute("""
        CREATE TRIGGER product_details_require_product_update
        BEFORE UPDATE OF gift_id ON product_details
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'product')
          OR EXISTS (SELECT 1 FROM activity_details WHERE gift_id = NEW.gift_id)
        BEGIN SELECT RAISE(ABORT, 'product details require a product gift with no activity details'); END
    """)
    op.execute("""
        CREATE TRIGGER activity_details_require_activity_insert
        BEFORE INSERT ON activity_details
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'activity')
          OR EXISTS (SELECT 1 FROM product_details WHERE gift_id = NEW.gift_id)
        BEGIN SELECT RAISE(ABORT, 'activity details require an activity gift with no product details'); END
    """)
    op.execute("""
        CREATE TRIGGER activity_details_require_activity_update
        BEFORE UPDATE OF gift_id ON activity_details
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'activity')
          OR EXISTS (SELECT 1 FROM product_details WHERE gift_id = NEW.gift_id)
        BEGIN SELECT RAISE(ABORT, 'activity details require an activity gift with no product details'); END
    """)
    op.execute("""
        CREATE TRIGGER product_offers_require_product_insert
        BEFORE INSERT ON product_offers
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'product')
        BEGIN SELECT RAISE(ABORT, 'product offers require a product gift'); END
    """)
    op.execute("""
        CREATE TRIGGER product_offers_require_product_update
        BEFORE UPDATE OF gift_id ON product_offers
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'product')
        BEGIN SELECT RAISE(ABORT, 'product offers require a product gift'); END
    """)
    op.execute("""
        CREATE TRIGGER activity_offers_require_activity_insert
        BEFORE INSERT ON activity_offers
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'activity')
        BEGIN SELECT RAISE(ABORT, 'activity offers require an activity gift'); END
    """)
    op.execute("""
        CREATE TRIGGER activity_offers_require_activity_update
        BEFORE UPDATE OF gift_id ON activity_offers
        WHEN NOT EXISTS (SELECT 1 FROM gifts WHERE id = NEW.gift_id AND gift_type_code = 'activity')
        BEGIN SELECT RAISE(ABORT, 'activity offers require an activity gift'); END
    """)
    op.execute("""
        CREATE TRIGGER custom_field_machine_key_immutable
        BEFORE UPDATE OF machine_key ON custom_field_definitions
        FOR EACH ROW WHEN EXISTS (SELECT 1 FROM gift_custom_field_values WHERE field_definition_id = OLD.id)
        BEGIN SELECT RAISE(ABORT, 'machine_key is immutable after first value'); END
    """)


def downgrade() -> None:
    """Remove the fixed V1 schema in reverse dependency order."""
    for trigger in (
        "custom_field_machine_key_immutable", "activity_offers_require_activity_update",
        "activity_offers_require_activity_insert", "product_offers_require_product_update",
        "product_offers_require_product_insert", "activity_details_require_activity_update",
        "activity_details_require_activity_insert", "product_details_require_product_update",
        "product_details_require_product_insert", "gifts_require_active_type_update",
        "gifts_require_active_type_insert", "gift_type_active_v1_update", "gift_type_active_v1_insert",
    ):
        op.execute(f"DROP TRIGGER {trigger}")
    for index in (
        "ix_ai_runs_gift_id", "ix_audit_events_entity_id", "ix_audit_events_entity_type",
        "ix_audit_events_event_type", "ix_gift_images_sha256", "ix_gift_images_gift_id",
        "ix_gift_bundle_components_component_gift_id", "ix_gift_bundle_components_bundle_gift_id",
        "ix_activity_offers_gift_id", "ix_product_offers_gift_id", "ix_gifts_deleted_at",
        "ix_gifts_subcategory_code", "ix_gifts_canonical_name", "ix_gifts_gift_type_code",
        "ix_dimension_options_dimension_key",
    ):
        op.drop_index(index)
    for table in (
        "backup_records", "import_runs", "ai_runs", "audit_events", "gift_images",
        "gift_custom_field_values", "custom_field_definitions", "gift_bundle_components",
        "activity_offers", "product_offers", "activity_details", "product_details", "gifts",
        "dimension_options", "gift_type_definitions",
    ):
        op.drop_table(table)
