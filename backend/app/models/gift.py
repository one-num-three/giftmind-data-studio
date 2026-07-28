"""Shared gifts plus their product, activity, offer, and bundle details."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CURRENT_SCHEMA_VERSION, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Gift(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gifts"

    schema_version: Mapped[int] = mapped_column(Integer, default=CURRENT_SCHEMA_VERSION, nullable=False)
    gift_type_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("gift_type_definitions.code", ondelete="RESTRICT"), index=True, nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    short_description: Mapped[str | None] = mapped_column(Text)
    subcategory_code: Mapped[str | None] = mapped_column(String(128), index=True)
    is_customizable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bundle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(16))
    completeness_score: Mapped[int | None] = mapped_column(Integer)
    recipient_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    relationship_stages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    age_ranges: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    traits: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interests: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    occasions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    desired_feelings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    memory_hooks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    custom_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    lead_days_min: Mapped[int | None] = mapped_column(Integer)
    lead_days_max: Mapped[int | None] = mapped_column(Integer)
    rush_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    taboo_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    allergy_notes: Mapped[str | None] = mapped_column(Text)
    safety_notes: Mapped[str | None] = mapped_column(Text)
    unsuitable_groups: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    why_template: Mapped[str | None] = mapped_column(Text)
    best_scenarios: Mapped[str | None] = mapped_column(Text)
    unsuitable_scenarios: Mapped[str | None] = mapped_column(Text)
    purchase_or_booking_tip: Mapped[str | None] = mapped_column(Text)
    ritual_tip: Mapped[str | None] = mapped_column(Text)
    pairing_ideas: Mapped[str | None] = mapped_column(Text)
    collector_notes: Mapped[str | None] = mapped_column(Text)
    source_notes: Mapped[str | None] = mapped_column(Text)
    source_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence_level: Mapped[str | None] = mapped_column(String(32))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        CheckConstraint("schema_version >= 1", name="ck_gifts_schema_version"),
        CheckConstraint("completeness_score IS NULL OR completeness_score BETWEEN 0 AND 100", name="ck_gifts_completeness_score"),
        CheckConstraint("price_min IS NULL OR price_min >= 0", name="ck_gifts_price_min_nonnegative"),
        CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_gifts_price_max_nonnegative"),
        CheckConstraint("price_min IS NULL OR price_max IS NULL OR price_min <= price_max", name="ck_gifts_price_range"),
        CheckConstraint("lead_days_min IS NULL OR lead_days_min >= 0", name="ck_gifts_lead_min_nonnegative"),
        CheckConstraint("lead_days_max IS NULL OR lead_days_max >= 0", name="ck_gifts_lead_max_nonnegative"),
        CheckConstraint("lead_days_min IS NULL OR lead_days_max IS NULL OR lead_days_min <= lead_days_max", name="ck_gifts_lead_range"),
    )


class ProductDetail(Base, TimestampMixin):
    __tablename__ = "product_details"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), primary_key=True)
    product_form: Mapped[str] = mapped_column(String(32), nullable=False)
    generic_product_name: Mapped[str | None] = mapped_column(String(256))
    materials: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    colors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    sizes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    specifications: Mapped[dict | list | None] = mapped_column(JSON)
    variant_notes: Mapped[str | None] = mapped_column(Text)
    weight_grams: Mapped[int | None] = mapped_column(Integer)
    package_dimensions: Mapped[str | None] = mapped_column(String(128))
    size_class: Mapped[str | None] = mapped_column(String(64))
    is_bulky: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    storage_requirements: Mapped[str | None] = mapped_column(Text)
    personalization_methods: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    personalization_requirements: Mapped[str | None] = mapped_column(Text)
    device_or_platform_compatibility: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    digital_delivery_method: Mapped[str | None] = mapped_column(String(128))
    shipping_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shipping_notes: Mapped[str | None] = mapped_column(Text)
    return_risk_notes: Mapped[str | None] = mapped_column(Text)
    warranty_expectation: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("weight_grams IS NULL OR weight_grams >= 0", name="ck_product_weight_nonnegative"),
        CheckConstraint("shelf_life_days IS NULL OR shelf_life_days >= 0", name="ck_product_shelf_life_nonnegative"),
    )


class ProductOffer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_offers"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant: Mapped[str] = mapped_column(String(256), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(256))
    offer_name: Mapped[str | None] = mapped_column(String(256))
    sku_or_model: Mapped[str | None] = mapped_column(String(256))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    stock_status: Mapped[str | None] = mapped_column(String(64))
    ship_from: Mapped[str | None] = mapped_column(String(256))
    service_regions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    delivery_days: Mapped[int | None] = mapped_column(Integer)
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    purchase_url: Mapped[str | None] = mapped_column(Text)
    return_policy: Mapped[str | None] = mapped_column(Text)
    warranty_policy: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("current_price IS NULL OR current_price >= 0", name="ck_product_offer_price_nonnegative"),
        CheckConstraint("delivery_days IS NULL OR delivery_days >= 0", name="ck_product_offer_delivery_nonnegative"),
        CheckConstraint("shipping_cost IS NULL OR shipping_cost >= 0", name="ck_product_offer_shipping_nonnegative"),
    )


class ActivityDetail(Base, TimestampMixin):
    __tablename__ = "activity_details"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), primary_key=True)
    activity_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_category: Mapped[str | None] = mapped_column(String(128))
    service_regions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    duration_minutes_min: Mapped[int | None] = mapped_column(Integer)
    duration_minutes_max: Mapped[int | None] = mapped_column(Integer)
    participants_min: Mapped[int | None] = mapped_column(Integer)
    participants_max: Mapped[int | None] = mapped_column(Integer)
    pricing_unit: Mapped[str | None] = mapped_column(String(64))
    schedule_type: Mapped[str | None] = mapped_column(String(64))
    booking_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    booking_lead_days_min: Mapped[int | None] = mapped_column(Integer)
    booking_lead_days_max: Mapped[int | None] = mapped_column(Integer)
    validity_days: Mapped[int | None] = mapped_column(Integer)
    included_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    excluded_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    equipment_requirements: Mapped[str | None] = mapped_column(Text)
    age_restrictions: Mapped[str | None] = mapped_column(Text)
    height_restrictions: Mapped[str | None] = mapped_column(Text)
    health_restrictions: Mapped[str | None] = mapped_column(Text)
    accessibility_notes: Mapped[str | None] = mapped_column(Text)
    weather_dependency: Mapped[str | None] = mapped_column(String(64))
    indoor_outdoor: Mapped[str | None] = mapped_column(String(64))
    cancellation_expectation: Mapped[str | None] = mapped_column(Text)
    reschedule_expectation: Mapped[str | None] = mapped_column(Text)
    refund_expectation: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("duration_minutes_min IS NULL OR duration_minutes_min >= 0", name="ck_activity_duration_min_nonnegative"),
        CheckConstraint("duration_minutes_max IS NULL OR duration_minutes_max >= 0", name="ck_activity_duration_max_nonnegative"),
        CheckConstraint("duration_minutes_min IS NULL OR duration_minutes_max IS NULL OR duration_minutes_min <= duration_minutes_max", name="ck_activity_duration_range"),
        CheckConstraint("participants_min IS NULL OR participants_min >= 0", name="ck_activity_participants_min_nonnegative"),
        CheckConstraint("participants_max IS NULL OR participants_max >= 0", name="ck_activity_participants_max_nonnegative"),
        CheckConstraint("participants_min IS NULL OR participants_max IS NULL OR participants_min <= participants_max", name="ck_activity_participants_range"),
        CheckConstraint("booking_lead_days_min IS NULL OR booking_lead_days_min >= 0", name="ck_activity_booking_lead_min_nonnegative"),
        CheckConstraint("booking_lead_days_max IS NULL OR booking_lead_days_max >= 0", name="ck_activity_booking_lead_max_nonnegative"),
        CheckConstraint("booking_lead_days_min IS NULL OR booking_lead_days_max IS NULL OR booking_lead_days_min <= booking_lead_days_max", name="ck_activity_booking_lead_range"),
        CheckConstraint("validity_days IS NULL OR validity_days >= 0", name="ck_activity_validity_nonnegative"),
    )


class ActivityOffer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activity_offers"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(256), nullable=False)
    offer_name: Mapped[str | None] = mapped_column(String(256))
    city: Mapped[str | None] = mapped_column(String(128))
    venue_name: Mapped[str | None] = mapped_column(String(256))
    address: Mapped[str | None] = mapped_column(Text)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    service_regions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    current_price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    current_price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CNY", nullable=False)
    pricing_unit: Mapped[str | None] = mapped_column(String(64))
    opening_hours_or_schedule_notes: Mapped[str | None] = mapped_column(Text)
    availability_status: Mapped[str | None] = mapped_column(String(64))
    booking_url: Mapped[str | None] = mapped_column(Text)
    booking_contact: Mapped[str | None] = mapped_column(String(256))
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    reschedule_policy: Mapped[str | None] = mapped_column(Text)
    refund_policy: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("current_price_min IS NULL OR current_price_min >= 0", name="ck_activity_offer_price_min_nonnegative"),
        CheckConstraint("current_price_max IS NULL OR current_price_max >= 0", name="ck_activity_offer_price_max_nonnegative"),
        CheckConstraint("current_price_min IS NULL OR current_price_max IS NULL OR current_price_min <= current_price_max", name="ck_activity_offer_price_range"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_activity_offer_longitude"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_activity_offer_latitude"),
    )


class GiftBundleComponent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "gift_bundle_components"

    bundle_gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="RESTRICT"), nullable=False, index=True)
    component_gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="RESTRICT"), nullable=False, index=True)
    component_type_code: Mapped[str | None] = mapped_column(String(64))
    component_name: Mapped[str | None] = mapped_column(String(256))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("bundle_gift_id <> component_gift_id", name="ck_bundle_component_not_self"),
        CheckConstraint("quantity >= 1", name="ck_bundle_component_quantity"),
        CheckConstraint("display_order >= 0", name="ck_bundle_component_display_order"),
    )
