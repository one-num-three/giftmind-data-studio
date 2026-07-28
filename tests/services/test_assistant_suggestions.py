import pytest

from backend.app.services.assistant_suggestions import generate_assistant_result, suggestion_to_patches


def test_patch_normalizer_drops_unknown_paths_and_clamps_confidence():
    raw = {
        "priceMin": 39,
        "unknownSecret": "x",
        "confidence": 4,
    }

    patches = suggestion_to_patches(raw, [{"label": "用户描述"}])

    assert [item["path"] for item in patches] == ["priceMin"]
    assert patches[0]["label"] == "最低价格"
    assert patches[0]["confidence"] == 1
    assert patches[0]["sourceRefs"] == ["用户描述"]
    assert patches[0]["status"] == "pending"


def test_patch_normalizer_flattens_product_and_activity_fields():
    product = suggestion_to_patches(
        {
            "shortDescription": "南京主题黄铜书签。",
            "recipientTypes": ["朋友", "", "朋友"],
            "productDetails": {
                "materials": ["黄铜"],
                "personalizationMethods": ["刻字"],
                "shippingRequired": True,
                "notAllowed": "drop",
            },
            "confidence": 0.91,
        },
        [{"label": "商品页", "url": "https://example.com"}],
    )
    activity = suggestion_to_patches(
        {
            "activityDetails": {
                "durationMinutesMin": 90,
                "participantsMax": 4,
                "bookingRequired": True,
                "serviceRegions": ["南京"],
            },
            "confidence": 0.82,
        },
        [{"label": "用户描述"}],
    )

    assert {item["path"] for item in product} == {
        "shortDescription",
        "recipientTypes",
        "productDetails.materials",
        "productDetails.personalizationMethods",
        "productDetails.shippingRequired",
    }
    assert next(item for item in product if item["path"] == "recipientTypes")["value"] == ["朋友"]
    assert {item["path"] for item in activity} == {
        "activityDetails.durationMinutesMin",
        "activityDetails.participantsMax",
        "activityDetails.bookingRequired",
        "activityDetails.serviceRegions",
    }


def test_patch_normalizer_uses_per_field_confidence_and_omits_empty_values():
    patches = suggestion_to_patches(
        {
            "priceMin": None,
            "tags": [],
            "whyTemplate": "适合表达心意。",
            "confidence": 0.55,
            "fieldConfidence": {"whyTemplate": 0.87},
        },
        [],
    )

    assert patches == [
        {
            "path": "whyTemplate",
            "label": "送礼理由",
            "value": "适合表达心意。",
            "confidence": 0.87,
            "sourceRefs": ["用户描述"],
            "status": "pending",
        }
    ]


@pytest.mark.asyncio
async def test_deepseek_v4_flash_receives_image_content(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"shortDescription":"图中礼物"}'}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, **kwargs):
            captured.update(kwargs["json"])
            return Response()

    monkeypatch.setattr("backend.app.services.assistant_suggestions.httpx.AsyncClient", lambda **_kwargs: Client())
    result = await generate_assistant_result(
        content="识别图片",
        gift_type_code="product",
        current_values={},
        history=[],
        source_refs=[{"label": "用户上传图片", "status": "ok"}],
        image_attachments=[{"mimeType": "image/png", "data": "data:image/png;base64,AAAA"}],
        api_key="sk-test",
    )

    assert captured["model"] == "deepseek-v4-flash"
    latest = captured["messages"][-1]["content"]
    assert isinstance(latest, list)
    assert any(part.get("type") == "image_url" for part in latest)
    assert result["source"] == "deepseek"
