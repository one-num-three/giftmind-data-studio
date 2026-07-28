"""Dashboard summary API tests."""

import asyncio
from datetime import UTC, datetime, timedelta

from backend.app.models.gift import ProductOffer
from tests.api.test_gifts import create_client, login, product_payload


def activity_payload(name: str = "陶艺体验") -> dict:
    return {
        "giftTypeCode": "activity",
        "canonicalName": name,
        "status": "draft",
        "activityDetails": {"activityMode": "offline"},
    }


def add_stale_offer(client, gift_id: str) -> None:
    """Persist a real old channel so stale-channel aggregation has a boundary."""
    async def seed() -> None:
        async with client.app.state.session_factory() as session:
            session.add(
                ProductOffer(
                    gift_id=gift_id,
                    merchant="老店",
                    active=True,
                    verified_at=datetime.now(UTC) - timedelta(days=31),
                )
            )
            await session.commit()

    asyncio.run(seed())


def test_dashboard_summarizes_active_product_and_activity_maintenance(tmp_path):
    """Catches dashboard totals that include deleted rows or omit maintenance signals."""
    with create_client(tmp_path) as client:
        login(client)
        complete = client.post("/api/gifts", json={**product_payload("完整商品"), "status": "active"})
        incomplete = client.post("/api/gifts", json=activity_payload())
        inactive = client.post("/api/gifts", json={**product_payload("停用商品"), "status": "inactive"})
        deleted = client.post("/api/gifts", json={**product_payload("已删除商品"), "status": "active"})
        assert all(response.status_code == 201 for response in (complete, incomplete, inactive, deleted))
        assert client.delete(f"/api/gifts/{deleted.json()['id']}").status_code == 204
        add_stale_offer(client, complete.json()["id"])

        response = client.get("/api/dashboard")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total"] == 3
    assert summary["complete"] == 1
    assert summary["drafts"] == 1
    assert summary["needsReview"] == 1
    assert summary["inactive"] == 1
    assert summary["productCount"] == 2
    assert summary["activityCount"] == 1
    assert summary["missingImages"] == 3
    assert summary["missingSources"] == 3
    assert summary["staleChannels"] == 1
    assert summary["possibleDuplicates"] == 0
    assert any(event["eventType"] == "gift.created" for event in summary["recentChanges"])
