from backend.app.schemas.gift import GiftCreateAdapter
from backend.scripts.import_h5_seed import seed_to_gift_payload


def test_seed_product_maps_to_complete_typed_payload():
    payload = seed_to_gift_payload(
        {
            "name": "定制声音卡片",
            "kind": "product",
            "format": "custom_product",
            "pricing": {"min": 99, "max": 159},
            "planning": {"recommendedLeadDays": 5},
            "fit": {"recipients": ["friend"], "occasions": ["birthday"], "tags": ["纪念感"]},
            "why": "把声音留成纪念。",
        },
        status="active",
    )
    model = GiftCreateAdapter.validate_python(payload)
    assert model.gift_type_code == "product"
    assert model.status == "active"
    assert model.is_customizable is True
    assert model.product_details.personalization_methods


def test_seed_activity_maps_to_activity_detail():
    payload = seed_to_gift_payload(
        {
            "name": "双人陶艺体验",
            "kind": "activity",
            "pricing": {"min": 199, "max": 399, "basis": "per_booking"},
            "planning": {"recommendedLeadDays": 7},
            "fit": {"recipients": ["partner"], "occasions": ["anniversary"]},
            "why": "一起完成一件作品。",
        }
    )
    model = GiftCreateAdapter.validate_python(payload)
    assert model.gift_type_code == "activity"
    assert model.activity_details.booking_required is True
