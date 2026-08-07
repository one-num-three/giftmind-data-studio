"""Contract tests for server-side H5 shares and recipient replies."""

from tests.api.test_gifts import create_client


def plan_payload() -> dict:
    return {
        "schemaVersion": "giftmind.plan.v1",
        "id": "plan-local-1",
        "title": "给小雨的一份心意",
        "subtitle": "围绕生日挑出的可执行方案",
        "insight": {"summary": "你们一起看过极光，这份礼物回应那段记忆。"},
        "gifts": [
            {
                "id": "g1",
                "catalogId": "g1",
                "name": "黄铜书签",
                "emoji": "🎁",
                "why": "适合喜欢阅读的 TA",
                "price": "¥39",
                "matchScore": 88,
                "category": "实物",
                "tip": "确认款式",
                "leadTime": "通常可当天准备",
                "kind": "product",
            }
        ],
        "letter": {"salutation": "给小雨：", "paragraphs": ["正文。"], "signature": "—— 我", "tone": "温暖"},
        "ritual": [{"time": "送出当天", "title": "留一点安静", "desc": "让对方先看到礼物和信。"}],
        "profile": {"recipient": "女朋友 / 妻子", "occasion": "生日", "memory": "我们第一次看极光"},
        "answers": {"recipient": "女朋友 / 妻子", "memory": "我们第一次看极光"},
        "share": {"greeting": "有一份为你认真准备的心意", "coverEmoji": "🎁", "theme": "warm"},
    }


def test_share_create_fetch_update_and_recipient_projection(tmp_path):
    with create_client(tmp_path) as client:
        created = client.post("/api/h5/shares", json={"plan": plan_payload(), "config": {"theme": "dawn"}})
        assert created.status_code == 201, created.text
        record = created.json()
        share_id = record["shareId"]
        assert record["slug"]
        assert record["planId"] == "plan-local-1"

        fetched = client.get(f"/api/h5/shares/{share_id}")
        assert fetched.status_code == 200
        plan = fetched.json()["plan"]
        assert plan["title"] == "给小雨的一份心意"
        assert plan["letter"]["paragraphs"] == ["正文。"]
        assert plan["ritual"]
        # Recipient-safe projection: no interview, prices, scores, or catalog ids.
        assert "answers" not in plan
        assert "profile" not in plan
        assert "price" not in plan["gifts"][0]
        assert "matchScore" not in plan["gifts"][0]
        assert "catalogId" not in plan["gifts"][0]
        assert plan["gifts"][0]["name"] == "黄铜书签"
        assert plan["gifts"][0]["why"]
        assert fetched.json()["config"]["theme"] == "dawn"

        updated = client.put(
            f"/api/h5/shares/{share_id}",
            json={"plan": {**plan_payload(), "title": "改后的标题"}, "config": {"theme": "sage"}},
        )
        assert updated.status_code == 200
        assert updated.json()["config"]["theme"] == "sage"
        assert client.get(f"/api/h5/shares/{share_id}").json()["plan"]["title"] == "改后的标题"


def test_share_replies_are_persisted_and_queryable_by_plan(tmp_path):
    with create_client(tmp_path) as client:
        created = client.post("/api/h5/shares", json={"plan": plan_payload(), "config": {}})
        share_id = created.json()["shareId"]

        first = client.post(f"/api/h5/shares/{share_id}/replies", json={"content": "谢谢你"})
        second = client.post(
            f"/api/h5/shares/{share_id}/replies",
            json={"content": "很喜欢", "reaction": "心动"},
        )
        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["reaction"] == "心动"

        by_share = client.get(f"/api/h5/shares/{share_id}/replies").json()
        assert [item["content"] for item in by_share] == ["谢谢你", "很喜欢"]

        by_plan = client.get("/api/h5/shares/replies", params={"planId": "plan-local-1"}).json()
        assert [item["content"] for item in by_plan] == ["很喜欢", "谢谢你"]


def test_share_reply_validation_and_missing_share(tmp_path):
    with create_client(tmp_path) as client:
        missing = client.post("/api/h5/shares/not-there/replies", json={"content": "hi"})
        assert missing.status_code == 404

        created = client.post("/api/h5/shares", json={"plan": plan_payload(), "config": {}})
        share_id = created.json()["shareId"]
        blank = client.post(f"/api/h5/shares/{share_id}/replies", json={"content": "   "})
        assert blank.status_code == 422
        too_long = client.post(f"/api/h5/shares/{share_id}/replies", json={"content": "长" * 301})
        assert too_long.status_code == 422
        bad_plan = client.post("/api/h5/shares", json={"plan": {"gifts": []}, "config": {}})
        assert bad_plan.status_code == 422


def test_share_fetch_missing_returns_404(tmp_path):
    with create_client(tmp_path) as client:
        assert client.get("/api/h5/shares/unknown").status_code == 404
