import pytest

from backend.app.prompts.schemas import PlanComposeOutput
from backend.app.services.plan_ai_mapper import InvalidAIPlanError, compose_ai_plan


def _candidate(number: int) -> dict:
    return {
        "catalogId": f"gift-{number}",
        "name": f"目录礼物 {number}",
        "kind": "product",
        "priceMin": number * 10,
        "priceMax": number * 20,
        "score": 90 - number,
        "emoji": "🎁",
    }


def _output(ids=("gift-1", "gift-2", "gift-3")) -> PlanComposeOutput:
    return PlanComposeOutput.model_validate(
        {
            "title": "认真挑选的三件礼物",
            "subtitle": "都来自已审核候选",
            "relationshipInsight": "这次更适合克制、具体地表达在意。",
            "selected": [
                {"catalogId": catalog_id, "rank": rank, "why": f"推荐理由 {rank}"}
                for rank, catalog_id in enumerate(ids, start=1)
            ],
            "letter": {"salutation": "给你：", "body": "第一段。\n第二段。", "closing": "—— 我"},
            "ritual": [{"title": "递出礼物", "description": "先让对方读信。", "timing": "当天"}],
        }
    )


def test_ai_plan_keeps_catalog_facts_and_maps_copy_to_h5_contract():
    plan = compose_ai_plan(
        {"recipient": "朋友", "occasion": "生日", "personality": ["文艺"]},
        [_candidate(1), _candidate(2), _candidate(3)],
        _output(),
        request_id="req-ai",
        model="deepseek-v4-flash",
        prompt_version="plan_compose_v1",
    )

    assert plan["source"] == "deepseek"
    assert plan["gifts"][0]["name"] == "目录礼物 1"
    assert plan["gifts"][0]["price"] == "¥10–20"
    assert plan["gifts"][0]["why"] == "推荐理由 1"
    assert plan["letter"]["paragraphs"] == ["第一段。", "第二段。"]
    assert plan["ritual"][0] == {"time": "当天", "title": "递出礼物", "desc": "先让对方读信。"}


def test_ai_plan_rejects_catalog_ids_outside_whitelist():
    with pytest.raises(InvalidAIPlanError):
        compose_ai_plan(
            {},
            [_candidate(1), _candidate(2), _candidate(3)],
            _output(("gift-1", "gift-2", "made-up")),
            request_id="req-invalid",
            model="deepseek-v4-flash",
            prompt_version="plan_compose_v1",
        )
