"""Completeness and similarity checks at the gift-domain boundary."""

from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.completeness import calculate_completeness
from backend.app.services.duplicates import normalize_name


def test_product_reaches_100_only_when_common_and_product_fields_are_present():
    """Catches a completeness score that ignores missing type-specific data."""
    complete = SimpleNamespace(
        gift_type_code="product",
        canonical_name="黄铜书签",
        recipient_types=["friend"],
        occasions=["birthday"],
        price_min=Decimal("39.00"),
        price_max=Decimal("39.00"),
        why_template="适合喜欢阅读的人。",
        product_details=SimpleNamespace(
            product_form="physical", generic_product_name="书签", materials=["黄铜"], shipping_required=True
        ),
        activity_details=None,
    )
    incomplete = SimpleNamespace(**{**complete.__dict__, "product_details": SimpleNamespace(
        product_form="physical", generic_product_name="书签", materials=[], shipping_required=True
    )})

    assert calculate_completeness(complete).score == 100
    result = calculate_completeness(incomplete)
    assert result.score < 100
    assert "product_details.materials" in result.missing_fields


def test_duplicate_normalization_ignores_surrounding_and_repeated_whitespace():
    """Catches duplicate checks that let spacing variants create the same gift."""
    assert normalize_name("  黄铜　书签  ") == normalize_name("黄铜 书签")
