"""Public request-contract tests for typed gifts."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.gift import ActivityGiftCreate, GiftCreateAdapter, ProductGiftCreate


def test_product_rejects_activity_details():
    """Catches a product request that could persist activity-only fields."""
    with pytest.raises(ValidationError):
        ProductGiftCreate.model_validate(
            {
                "gift_type_code": "product",
                "canonical_name": "书签",
                "activity_details": {"activity_mode": "offline"},
            }
        )


def test_activity_accepts_activity_details():
    """Catches a discriminated union that cannot select a valid activity payload."""
    value = GiftCreateAdapter.validate_python(
        {
            "gift_type_code": "activity",
            "canonical_name": "陶艺课",
            "activity_details": {
                "activity_mode": "offline",
                "duration_minutes_min": 90,
                "duration_minutes_max": 120,
                "participants_min": 2,
                "participants_max": 2,
                "pricing_unit": "per_session",
            },
        }
    )

    assert isinstance(value, ActivityGiftCreate)
    assert value.gift_type_code == "activity"


def test_gift_contract_rejects_free_price_and_digital_delivery_conflicts():
    """Catches payloads that contradict the shared free-price and digital rules."""
    with pytest.raises(ValidationError):
        ProductGiftCreate.model_validate(
            {
                "gift_type_code": "product",
                "canonical_name": "电子礼品卡",
                "is_free": True,
                "price_min": "1.00",
                "product_details": {"product_form": "digital", "shipping_required": True},
            }
        )
