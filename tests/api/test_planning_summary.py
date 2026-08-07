"""Contract tests for the H5 summary confirmation endpoint."""

from tests.api.test_gifts import create_client


def _answers() -> dict:
    return {
        "recipient": "女朋友 / 妻子",
        "occasion": "纪念日",
        "timing": "一周内",
        "budget": "¥300–600",
        "taboo": ["不要花 / 香水等易踩雷"],
        "style": ["体验类（活动/课程/旅行）"],
        "memory": "我们第一次在冰岛看极光，一起捡了一块鹅卵石。",
        "feeling": "被深深理解，感动到想哭",
    }


def test_summary_derives_four_editable_blocks(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post(
            "/api/h5/plans/summary",
            json={"requestId": "summary-1", "answers": _answers()},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requestId"] == "summary-1"
    assert payload["source"] == "rule"
    summary = payload["summary"]
    assert set(summary) == {"who", "story", "feeling", "constraints"}
    assert "女朋友" in summary["who"]["text"]
    assert "冰岛" in summary["story"]["text"]
    assert "被深深理解" in summary["feeling"]["text"]
    assert "¥300–600" in summary["constraints"]["text"]
    assert "不要花" in summary["constraints"]["text"]
    assert summary["who"]["fields"] == ["recipient"]
    assert summary["story"]["fields"] == ["memory"]
    assert summary["feeling"]["fields"] == ["feeling"]


def test_summary_handles_sparse_answers_with_fallbacks(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post(
            "/api/h5/plans/summary",
            json={"requestId": "summary-2", "answers": {"recipient": "闺蜜 / 好友"}},
        )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "闺蜜" in summary["who"]["text"]
    assert "还没有提到" in summary["story"]["text"]
    assert summary["constraints"]["text"] == "暂无特殊约束"
