"""Gift collection filtering and lifecycle query tests."""

from tests.api.test_dashboard import activity_payload
from tests.api.test_gifts import create_client, login, product_payload


def test_gift_list_filters_and_explicit_deleted_scope(tmp_path):
    """Catches a list endpoint that leaks deleted records or ignores documented filters."""
    with create_client(tmp_path) as client:
        login(client)
        product = client.post("/api/gifts", json={**product_payload("黄铜书签"), "status": "active"})
        activity = client.post("/api/gifts", json=activity_payload("植物染体验"))
        deleted = client.post("/api/gifts", json={**product_payload("已归档书签"), "status": "active"})
        assert all(response.status_code == 201 for response in (product, activity, deleted))
        assert client.delete(f"/api/gifts/{deleted.json()['id']}").status_code == 204

        default_list = client.get("/api/gifts")
        search = client.get("/api/gifts", params={"q": "黄铜", "giftType": "product", "status": "active", "deleted": "exclude"})
        recycle = client.get("/api/gifts", params={"deleted": "only"})

    assert default_list.status_code == 200
    assert default_list.json()["total"] == 2
    assert [item["canonicalName"] for item in search.json()["items"]] == ["黄铜书签"]
    assert recycle.status_code == 200
    assert recycle.json()["total"] == 1
    assert recycle.json()["items"][0]["canonicalName"] == "已归档书签"


def test_bulk_status_change_updates_each_active_gift_and_audits_each_row(tmp_path):
    """Catches a bulk update that reports a count without changing every selected record."""
    with create_client(tmp_path) as client:
        login(client)
        first = client.post("/api/gifts", json=product_payload("批量商品一"))
        second = client.post("/api/gifts", json=activity_payload("批量活动二"))
        assert first.status_code == second.status_code == 201

        changed = client.patch(
            "/api/gifts/bulk/status",
            json={"giftIds": [first.json()["id"], second.json()["id"]], "status": "active"},
        )
        dashboard = client.get("/api/dashboard")

    assert changed.status_code == 200
    assert changed.json() == {"affected": 2}
    assert client.get(f"/api/gifts/{first.json()['id']}").json()["status"] == "active"
    audit_ids = [event["entityId"] for event in dashboard.json()["recentChanges"] if event["eventType"] == "gift.status_changed"]
    assert {first.json()["id"], second.json()["id"]}.issubset(set(audit_ids))


def test_bulk_status_rejects_unknown_lifecycle_status(tmp_path):
    """Catches bulk operations that persist arbitrary status strings outside the lifecycle."""
    with create_client(tmp_path) as client:
        login(client)
        gift = client.post("/api/gifts", json=product_payload("状态受限礼物"))
        assert gift.status_code == 201

        changed = client.patch(
            "/api/gifts/bulk/status",
            json={"giftIds": [gift.json()["id"]], "status": "published"},
        )

    assert changed.status_code == 422
