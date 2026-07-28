"""Typed input and output contracts for product and activity gifts."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, Field, TypeAdapter, field_validator, model_validator

from backend.app.schemas.common import APIModel, normalize_text


NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeAmount = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductDetailsInput(APIModel):
    product_form: Literal["physical", "digital", "hybrid"]
    generic_product_name: str | None = None
    materials: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    specifications: dict | list | None = None
    variant_notes: str | None = None
    weight_grams: NonNegativeInt | None = None
    package_dimensions: str | None = None
    size_class: str | None = None
    is_bulky: bool = False
    is_fragile: bool = False
    is_consumable: bool = False
    shelf_life_days: NonNegativeInt | None = None
    storage_requirements: str | None = None
    personalization_methods: list[str] = Field(default_factory=list)
    personalization_requirements: str | None = None
    device_or_platform_compatibility: list[str] = Field(default_factory=list)
    digital_delivery_method: str | None = None
    shipping_required: bool = False
    shipping_notes: str | None = None
    return_risk_notes: str | None = None
    warranty_expectation: str | None = None

    @model_validator(mode="after")
    def validate_delivery_mode(self) -> "ProductDetailsInput":
        if self.product_form == "digital":
            if self.shipping_required:
                raise ValueError("digital products cannot require shipping")
            if not self.digital_delivery_method:
                raise ValueError("digital products require a digital_delivery_method")
        if self.product_form == "physical" and self.digital_delivery_method:
            raise ValueError("physical products cannot have a digital_delivery_method")
        return self


class ActivityDetailsInput(APIModel):
    activity_mode: Literal["online", "offline", "hybrid"]
    activity_category: str | None = None
    service_regions: list[str] = Field(default_factory=list)
    duration_minutes_min: NonNegativeInt | None = None
    duration_minutes_max: NonNegativeInt | None = None
    participants_min: NonNegativeInt | None = None
    participants_max: NonNegativeInt | None = None
    pricing_unit: str | None = None
    schedule_type: str | None = None
    booking_required: bool = False
    booking_lead_days_min: NonNegativeInt | None = None
    booking_lead_days_max: NonNegativeInt | None = None
    validity_days: NonNegativeInt | None = None
    included_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    equipment_requirements: str | None = None
    age_restrictions: str | None = None
    height_restrictions: str | None = None
    health_restrictions: str | None = None
    accessibility_notes: str | None = None
    weather_dependency: str | None = None
    indoor_outdoor: str | None = None
    cancellation_expectation: str | None = None
    reschedule_expectation: str | None = None
    refund_expectation: str | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> "ActivityDetailsInput":
        _validate_range(self.duration_minutes_min, self.duration_minutes_max, "duration_minutes")
        _validate_range(self.participants_min, self.participants_max, "participants")
        _validate_range(self.booking_lead_days_min, self.booking_lead_days_max, "booking_lead_days")
        if self.activity_mode == "online" and self.weather_dependency:
            raise ValueError("online activities cannot have weather_dependency")
        return self


class BundleComponentInput(APIModel):
    component_gift_id: UUID
    component_type_code: str | None = None
    component_name: str | None = None
    quantity: Annotated[int, Field(ge=1)] = 1
    required: bool = True
    display_order: NonNegativeInt = 0
    role_notes: str | None = None


class GiftBase(APIModel):
    canonical_name: Annotated[str, Field(min_length=1, max_length=256)]
    aliases: list[Annotated[str, Field(min_length=1, max_length=256)]] = Field(default_factory=list)
    short_description: str | None = None
    subcategory_code: str | None = None
    is_customizable: bool = False
    is_bundle: bool = False
    bundle_components: list[BundleComponentInput] = Field(default_factory=list)
    status: str = "draft"
    emoji: str | None = None
    recipient_types: list[str] = Field(default_factory=list)
    relationship_stages: list[str] = Field(default_factory=list)
    age_ranges: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)
    desired_feelings: list[str] = Field(default_factory=list)
    memory_hooks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    custom_tags: list[str] = Field(default_factory=list)
    price_min: NonNegativeAmount | None = None
    price_max: NonNegativeAmount | None = None
    is_free: bool = False
    currency: Annotated[str, Field(min_length=3, max_length=3)] = "CNY"
    lead_days_min: NonNegativeInt | None = None
    lead_days_max: NonNegativeInt | None = None
    rush_available: bool = False
    taboo_flags: list[str] = Field(default_factory=list)
    allergy_notes: str | None = None
    safety_notes: str | None = None
    unsuitable_groups: list[str] = Field(default_factory=list)
    why_template: str | None = None
    best_scenarios: str | None = None
    unsuitable_scenarios: str | None = None
    purchase_or_booking_tip: str | None = None
    ritual_tip: str | None = None
    pairing_ideas: str | None = None
    collector_notes: str | None = None
    source_notes: str | None = None
    source_urls: list[AnyHttpUrl] = Field(default_factory=list)
    confidence_level: str | None = None
    verified_at: datetime | None = None

    @field_validator("canonical_name", mode="before")
    @classmethod
    def normalize_canonical_name(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("aliases", mode="after")
    @classmethod
    def normalize_aliases(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_text(alias) for alias in value))

    @model_validator(mode="after")
    def validate_common_rules(self) -> "GiftBase":
        _validate_range(self.price_min, self.price_max, "price")
        _validate_range(self.lead_days_min, self.lead_days_max, "lead_days")
        if self.is_free and (self.price_min is not None or self.price_max is not None):
            raise ValueError("free gifts cannot have a price")
        if not self.is_free and self.price_min == Decimal("0") and self.price_max == Decimal("0"):
            raise ValueError("zero-price gifts must be marked free")
        if self.is_bundle != bool(self.bundle_components):
            raise ValueError("bundle components are required only for bundles")
        return self


class ProductGiftCreate(GiftBase):
    gift_type_code: Literal["product"]
    product_details: ProductDetailsInput
    activity_details: None = None

    @model_validator(mode="after")
    def validate_customization(self) -> "ProductGiftCreate":
        if self.is_customizable and not self.product_details.personalization_methods:
            raise ValueError("customizable products require personalization_methods")
        return self


class ActivityGiftCreate(GiftBase):
    gift_type_code: Literal["activity"]
    activity_details: ActivityDetailsInput
    product_details: None = None


GiftCreate = Annotated[ProductGiftCreate | ActivityGiftCreate, Field(discriminator="gift_type_code")]
GiftCreateAdapter = TypeAdapter(GiftCreate)
GiftUpdate = GiftCreate


class GiftRead(APIModel):
    id: UUID
    schema_version: int
    gift_type_code: Literal["product", "activity"]
    canonical_name: str
    aliases: list[str]
    short_description: str | None
    subcategory_code: str | None
    is_customizable: bool
    is_bundle: bool
    status: str
    emoji: str | None
    completeness_score: int | None
    recipient_types: list[str]
    relationship_stages: list[str]
    age_ranges: list[str]
    traits: list[str]
    interests: list[str]
    occasions: list[str]
    desired_feelings: list[str]
    memory_hooks: list[str]
    tags: list[str]
    custom_tags: list[str]
    price_min: Decimal | None
    price_max: Decimal | None
    is_free: bool
    currency: str
    lead_days_min: int | None
    lead_days_max: int | None
    rush_available: bool
    taboo_flags: list[str]
    allergy_notes: str | None
    safety_notes: str | None
    unsuitable_groups: list[str]
    why_template: str | None
    best_scenarios: str | None
    unsuitable_scenarios: str | None
    purchase_or_booking_tip: str | None
    ritual_tip: str | None
    pairing_ideas: str | None
    collector_notes: str | None
    source_notes: str | None
    source_urls: list[str]
    confidence_level: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    product_details: ProductDetailsInput | None = None
    activity_details: ActivityDetailsInput | None = None
    bundle_components: list[BundleComponentInput] = Field(default_factory=list)

    model_config = APIModel.model_config | {"from_attributes": True}


def _validate_range(minimum: Decimal | int | None, maximum: Decimal | int | None, field: str) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(f"{field}_min must not exceed {field}_max")
