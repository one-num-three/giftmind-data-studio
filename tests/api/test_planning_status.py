"""Local H5 service status contract tests."""

from tests.api.test_gifts import create_client, login, product_payload


def test_h5_status_is_public_and_reports_only_eligible_active_gifts(tmp_path):
    with create_client(tmp_path) as client:
        initial = client.get("/api/h5/status")
        login(client)
        created = client.post(
            "/api/gifts",
            json={**product_payload("可推荐书签"), "status": "active"},
        )
        assert created.status_code == 201
        ready = client.get("/api/h5/status")

    assert initial.status_code == 200
    assert initial.json()["activeGiftCount"] == 0
    assert ready.status_code == 200
    assert ready.json() == {
        "ok": True,
        "deepseekConfigured": False,
        "model": "deepseek-v4-flash",
        "activeGiftCount": 1,
        "mode": "rules",
        "voiceConfigured": False,
        "promptVersions": {
            "profileExtract": "profile_extract_v1",
            "planCompose": "plan_compose_v1",
        },
    }
