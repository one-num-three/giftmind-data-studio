"""Contract tests for the local H5 planning endpoints."""

from tests.api.test_gifts import create_client, login, product_payload


def _answers() -> dict:
    return {
        "recipient": "闺蜜 / 好友",
        "occasion": "生日",
        "timing": "一周内",
        "budget": "¥0–300",
        "personality": ["文艺 / 小众"],
        "taboo": [],
        "memory": "我们经常一起逛书店",
        "relationshipNote": "认识很多年的朋友",
        "feeling": "被深深理解，感动到想哭",
        "style": ["实物礼物"],
        "city": None,
    }


def test_generate_plan_uses_active_catalog_and_rule_fallback_without_key(tmp_path):
    with create_client(tmp_path) as client:
        login(client)
        ids = []
        for index, name in enumerate(("黄铜书签", "小型阅读灯", "手账贴纸"), start=1):
            response = client.post(
                "/api/gifts",
                json={
                    **product_payload(name),
                    "status": "active",
                    "priceMin": str(index * 20),
                    "priceMax": str(index * 30),
                    "tags": ["阅读", "文艺"],
                    "traits": ["文艺 / 小众"],
                },
            )
            assert response.status_code == 201
            ids.append(response.json()["id"])

        generated = client.post(
            "/api/h5/plans/generate",
            json={"requestId": "client-req-1", "answers": _answers()},
        )

    assert generated.status_code == 200, generated.text
    plan = generated.json()
    assert plan["schemaVersion"] == "giftmind.plan.v1"
    assert plan["source"] == "rule_fallback"
    assert plan["requestId"] == "client-req-1"
    assert len(plan["gifts"]) == 3
    assert {gift["catalogId"] for gift in plan["gifts"]} == set(ids)
    assert all(gift["name"] in {"黄铜书签", "小型阅读灯", "手账贴纸"} for gift in plan["gifts"])
    assert plan["letter"]["paragraphs"]
    assert plan["ritual"]


def test_generate_plan_never_silently_loosens_hard_constraints(tmp_path):
    with create_client(tmp_path) as client:
        generated = client.post(
            "/api/h5/plans/generate",
            json={"requestId": "client-empty", "answers": _answers()},
        )

    assert generated.status_code == 409
    assert generated.json()["detail"]["code"] == "NO_CANDIDATES"


def test_local_edit_endpoints_change_only_the_requested_section(tmp_path):
    with create_client(tmp_path) as client:
        login(client)
        ids = []
        for name in ("礼物甲", "礼物乙", "礼物丙", "礼物丁"):
            response = client.post(
                "/api/gifts",
                json={**product_payload(name), "status": "active", "priceMin": "20", "priceMax": "80"},
            )
            assert response.status_code == 201
            ids.append(response.json()["id"])

        replacement = client.post(
            "/api/h5/plans/gifts/replace",
            json={
                "requestId": "replace-1",
                "answers": _answers(),
                "currentCatalogIds": ids[:3],
                "replaceCatalogId": ids[0],
                "lockedCatalogIds": ids[1:3],
                "reason": "already_gifted",
            },
        )
        letter = client.post(
            "/api/h5/plans/letter/rewrite",
            json={
                "requestId": "letter-1",
                "answers": _answers(),
                "gifts": [],
                "currentLetter": {"salutation": "给你：", "paragraphs": ["原文。"], "signature": "—— 我"},
                "tone": "concise",
                "instruction": "再短一点。",
            },
        )
        ritual = client.post(
            "/api/h5/plans/ritual/rewrite",
            json={
                "requestId": "ritual-1",
                "answers": _answers(),
                "gifts": [],
                "currentRitual": [{"time": "当天", "title": "递出", "desc": "原步骤"}],
                "instruction": "先让对方读信",
            },
        )

    assert replacement.status_code == 200
    assert replacement.json()["gift"]["catalogId"] == ids[3]
    assert letter.status_code == 200
    assert letter.json()["letter"]["tone"] == "concise"
    assert letter.json()["letter"]["paragraphs"] == ["原文。", "再短一点。"]
    assert ritual.status_code == 200
    assert ritual.json()["ritual"][0]["desc"] == "先让对方读信"
