import pytest

from backend.app.services.assistant_suggestions import _fallback_raw, generate_assistant_result, suggestion_to_patches


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
            "reason": None,
            "evidence": [],
            "sourceRefs": ["用户描述"],
            "status": "pending",
        }
    ]


def test_fallback_turns_measurement_description_into_reviewable_facts():
    raw = _fallback_raw(
        "一个东南大学的圆形校徽冰箱贴，直径是 5 厘米",
        "product",
        [{"label": "用户描述", "status": "ok"}],
    )
    patches = suggestion_to_patches(raw, [{"label": "用户描述"}])
    values = {item["path"]: item["value"] for item in patches}

    assert values["canonicalName"] == "东南大学的圆形校徽冰箱贴"
    assert values["productDetails.genericProductName"] == "冰箱贴"
    assert values["productDetails.sizes"] == ["5 厘米"]
    assert "合适的对象" not in str(values.get("whyTemplate", ""))
    assert "校友" in str(values["whyTemplate"])
    assert next(item for item in patches if item["path"] == "productDetails.sizes")["evidence"]


@pytest.mark.asyncio
async def test_deepseek_v4_flash_receives_extracted_image_text_not_image_content(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"shortDescription":"图中礼物","whyTemplate":"因为{recipient}喜欢云南风味或火锅。野生菌底料能带来地道山珍体验。适合在{occasion}时共享。一起烹饪还能增加互动和仪式感。"}'}}]}

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
        source_refs=[{"label": "图片：gift.png", "status": "ok", "text": "OCR：黄铜书签，售价 69 元\n图片描述：礼盒装书签"}],
        api_key="sk-test",
    )

    assert captured["model"] == "deepseek-v4-flash"
    assert captured["thinking"] == {"type": "disabled"}
    latest = captured["messages"][-1]["content"]
    assert isinstance(latest, str)
    assert "黄铜书签" in latest
    assert "image_url" not in latest
    assert result["source"] == "deepseek"
    assert any(item["path"] == "productDetails.genericProductName" for item in result["patches"])
    why_patch = next(item for item in result["patches"] if item["path"] == "whyTemplate")
    assert "{" not in why_patch["value"]
    assert "收礼人" in why_patch["value"]
    reason_lines = why_patch["value"].splitlines()
    assert len(reason_lines) == 4
    assert all(line.startswith("- ") for line in reason_lines)


@pytest.mark.asyncio
async def test_assistant_proactively_asks_for_the_most_useful_missing_information():
    result = await generate_assistant_result(
        content="这是一个陶艺体验",
        gift_type_code="activity",
        current_values={
            "canonicalName": "双人陶艺体验",
            "priceMin": None,
            "priceMax": None,
            "recipientTypes": [],
            "occasions": [],
            "activityDetails": {"durationMinutesMin": None, "participantsMin": None, "bookingRequired": False},
        },
        history=[],
        source_refs=[{"label": "用户描述", "status": "ok"}],
        api_key=None,
    )

    assert 1 <= len(result["questions"]) <= 3
    assert any("价格" in question for question in result["questions"])
    assert "还需要确认" in result["content"]


@pytest.mark.asyncio
async def test_fallback_preserves_a_written_price_range():
    result = await generate_assistant_result(
        content="黄铜书签，预算 50 到 100 元",
        gift_type_code="product",
        current_values={},
        history=[],
        source_refs=[{"label": "用户描述", "status": "ok"}],
        api_key=None,
    )

    values = {patch["path"]: patch["value"] for patch in result["patches"]}
    assert values["priceMin"] == 50
    assert values["priceMax"] == 100


@pytest.mark.asyncio
async def test_clear_activity_words_override_product_default():
    result = await generate_assistant_result(
        content="和女朋友一起露营看星星",
        gift_type_code="product",
        current_values={},
        history=[],
        source_refs=[{"label": "用户描述", "status": "ok"}],
        api_key=None,
    )

    values = {patch["path"]: patch["value"] for patch in result["patches"]}
    assert values["giftTypeCode"] == "activity"
    assert not any(path.startswith("productDetails.") for path in values)


@pytest.mark.asyncio
async def test_shared_activity_without_intimate_relationship_stays_goods():
    result = await generate_assistant_result(
        content="和朋友一起露营看星星",
        gift_type_code="activity",
        current_values={},
        history=[],
        source_refs=[{"label": "用户描述", "status": "ok"}],
        api_key=None,
    )

    values = {patch["path"]: patch["value"] for patch in result["patches"]}
    assert values["giftTypeCode"] == "product"
    assert any("是什么关系" in question for question in result["questions"])


@pytest.mark.asyncio
async def test_experience_without_shared_participation_stays_goods():
    result = await generate_assistant_result(
        content="送一张单人SPA体验券给她",
        gift_type_code="activity",
        current_values={},
        history=[],
        source_refs=[{"label": "用户描述", "status": "ok"}],
        api_key=None,
    )

    values = {patch["path"]: patch["value"] for patch in result["patches"]}
    assert values["giftTypeCode"] == "product"
