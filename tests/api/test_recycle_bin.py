"""Soft-delete, restoration, and permanent purge API tests."""

from tests.api.test_gifts import create_client, login, product_payload


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
        assert client.delete(f"/api/recycle-bin/gifts/{gift_id}").status_code == 204
        assert client.get("/api/recycle-bin/gifts").json()["total"] == 0
