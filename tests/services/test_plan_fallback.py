from backend.app.services.plan_fallback import compose_rule_plan


def test_rule_plan_uses_catalog_facts_and_h5_shape():
    plan = compose_rule_plan(
        {
            "recipient": "女朋友 / 妻子",
            "occasion": "纪念日",
            "memory": "第一次旅行是在海边",
            "feeling": "被深深理解",
            "personality": ["文艺 / 小众"],
        },
        [
            {
                "catalogId": "gift-1",
                "name": "海边声音纪念卡",
                "kind": "product",
                "category": "定制",
                "priceMin": 99,
                "priceMax": 159,
                "score": 94,
                "whyTemplate": "把共同记忆变成可以反复打开的声音。",
                "purchaseOrBookingTip": "提前上传音频并确认试听。",
                "leadDaysMax": 5,
                "tags": ["纪念感", "可定制"],
                "emoji": "🌊",
            }
        ],
        request_id="req-1",
    )

    assert plan["schemaVersion"] == "giftmind.plan.v1"
    assert plan["source"] == "rule_fallback"
    assert plan["requestId"] == "req-1"
    assert plan["gifts"][0]["catalogId"] == "gift-1"
    assert plan["gifts"][0]["name"] == "海边声音纪念卡"
    assert plan["gifts"][0]["price"] == "¥99–159"
    assert "第一次旅行是在海边" in plan["insight"]["summary"]
    assert plan["ritual"][0]["desc"] == "提前上传音频并确认试听。"


def test_rule_plan_rejects_empty_candidate_set():
    try:
        compose_rule_plan({}, [], request_id="req-empty")
    except ValueError as exc:
        assert "eligible" in str(exc)
    else:
        raise AssertionError("expected an empty candidate set to be rejected")
