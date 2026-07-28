"""Deterministic completeness scoring for typed gifts."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class GiftAggregate(Protocol):
    """The persisted gift/detail shape required by completeness scoring."""

    gift_type_code: str
    canonical_name: str
    recipient_types: list[str]
    occasions: list[str]
    price_min: Decimal | None
    price_max: Decimal | None
    why_template: str | None
    product_details: object | None
    activity_details: object | None


@dataclass(frozen=True)
class CompletenessResult:
    score: int
    missing_fields: list[str]


_COMMON_FIELDS: tuple[tuple[str, int], ...] = (
    ("canonical_name", 10),
    ("recipient_types", 10),
    ("occasions", 10),
    ("price_range", 10),
    ("why_template", 20),
)
_PRODUCT_FIELDS: tuple[tuple[str, int], ...] = (
    ("product_form", 10),
    ("generic_product_name", 10),
    ("materials", 10),
    ("shipping_required", 10),
)
_ACTIVITY_FIELDS: tuple[tuple[str, int], ...] = (
    ("activity_mode", 10),
    ("duration_minutes", 10),
    ("participants", 10),
    ("pricing_unit", 10),
)


def calculate_completeness(gift: GiftAggregate) -> CompletenessResult:
    """Return a 0-100 score and the missing fields that prevented full completeness."""
    score = 0
    missing: list[str] = []
    for field, weight in _COMMON_FIELDS:
        if _common_present(gift, field):
            score += weight
        else:
            missing.append(field)

    detail = gift.product_details if gift.gift_type_code == "product" else gift.activity_details
    fields = _PRODUCT_FIELDS if gift.gift_type_code == "product" else _ACTIVITY_FIELDS
    detail_prefix = "product_details" if gift.gift_type_code == "product" else "activity_details"
    for field, weight in fields:
        if _detail_present(detail, field):
            score += weight
        else:
            missing.append(f"{detail_prefix}.{field}")
    return CompletenessResult(score=score, missing_fields=missing)


def _common_present(gift: GiftAggregate, field: str) -> bool:
    if field == "price_range":
        return gift.price_min is not None and gift.price_max is not None
    return bool(getattr(gift, field))


def _detail_present(detail: object | None, field: str) -> bool:
    if detail is None:
        return False
    if field == "duration_minutes":
        return getattr(detail, "duration_minutes_min", None) is not None and getattr(detail, "duration_minutes_max", None) is not None
    if field == "participants":
        return getattr(detail, "participants_min", None) is not None and getattr(detail, "participants_max", None) is not None
    value = getattr(detail, field, None)
    return value is not None and value != [] and value != ""
