"""Soft-delete, restoration, and permanent purge API tests."""

from tests.api.test_gifts import create_client, login, product_payload


def bundle_payload(name: str, component_gift_id: str) -> dict:
    payload = product_payload(name)
    payload.update(
        {
            "isBundle": True,
            "bundleComponents": [{"componentGiftId": component_gift_id}],
        }
    )
    return payload


def test_soft_delete_restore_and_purge_gift(tmp_path):
    """Catches a recycle-bin workflow that loses restorability or leaves purged rows behind."""
    with create_client(tmp_path) as client:
        login(client)
        created = client.post("/api/gifts", json=product_payload("可回收书签"))
        assert created.status_code == 201
        gift_id = created.json()["id"]

        assert client.delete(f"/api/gifts/{gift_id}").status_code == 204
        assert client.get("/api/gifts").json()["total"] == 0
        recycle = client.get("/api/recycle-bin/gifts")
        assert recycle.status_code == 200
        assert recycle.json()["total"] == 1

        restored = client.post(f"/api/recycle-bin/gifts/{gift_id}/restore")
        assert restored.status_code == 200
        assert restored.json()["deletedAt"] is None
        assert client.delete(f"/api/gifts/{gift_id}").status_code == 204
        assert client.request("DELETE",
            f"/api/recycle-bin/gifts/{gift_id}", json={"giftName": "可回收书签"}
        ).status_code == 204
        assert client.get("/api/recycle-bin/gifts").json()["total"] == 0


def test_purge_bundle_removes_its_component_references(tmp_path):
    """Catches a RESTRICT error when permanently deleting a bundle gift."""
    with create_client(tmp_path) as client:
        login(client)
        component = client.post("/api/gifts", json=product_payload("组件礼物"))
        assert component.status_code == 201
        bundle = client.post(
            "/api/gifts", json=bundle_payload("礼物组合", component.json()["id"])
        )
        assert bundle.status_code == 201

        bundle_id = bundle.json()["id"]
        assert client.delete(f"/api/gifts/{bundle_id}").status_code == 204
        assert client.request("DELETE",
            f"/api/recycle-bin/gifts/{bundle_id}", json={"giftName": "礼物组合"}
        ).status_code == 204
        assert client.get(f"/api/gifts/{component.json()['id']}").status_code == 200


def test_purge_component_removes_references_from_existing_bundles(tmp_path):
    """Catches a RESTRICT error when permanently deleting a bundle component."""
    with create_client(tmp_path) as client:
        login(client)
        component = client.post("/api/gifts", json=product_payload("待清除组件"))
        assert component.status_code == 201
        bundle = client.post(
            "/api/gifts", json=bundle_payload("仍保留的组合", component.json()["id"])
        )
        assert bundle.status_code == 201

        component_id = component.json()["id"]
        assert client.delete(f"/api/gifts/{component_id}").status_code == 204
        assert client.request("DELETE",
            f"/api/recycle-bin/gifts/{component_id}", json={"giftName": "待清除组件"}
        ).status_code == 204
        remaining_bundle = client.get(f"/api/gifts/{bundle.json()['id']}")
        assert remaining_bundle.status_code == 200
        assert remaining_bundle.json()["bundleComponents"] == []


def test_purge_requires_the_exact_typed_gift_name(tmp_path):
    """Catches a permanent-delete route that accepts a missing or incorrect confirmation."""
    with create_client(tmp_path) as client:
        login(client)
        created = client.post("/api/gifts", json=product_payload("需确认删除"))
        assert created.status_code == 201
        gift_id = created.json()["id"]
        assert client.delete(f"/api/gifts/{gift_id}").status_code == 204

        missing = client.delete(f"/api/recycle-bin/gifts/{gift_id}")
        wrong = client.request("DELETE",
            f"/api/recycle-bin/gifts/{gift_id}", json={"giftName": "错误名称"}
        )
        confirmed = client.request("DELETE",
            f"/api/recycle-bin/gifts/{gift_id}", json={"giftName": "需确认删除"}
        )

    assert missing.status_code == 422
    assert wrong.status_code == 422
    assert confirmed.status_code == 204
