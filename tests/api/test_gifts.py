"""End-to-end typed gift collection API tests."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.taxonomy import GiftTypeDefinition


def create_client(tmp_path) -> TestClient:
    database_path = tmp_path / "gifts.sqlite3"
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    async def initialize() -> None:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                GiftTypeDefinition.__table__.insert(),
                [
                    {"code": "product", "name": "商品", "status": "active", "contract_version": 1},
                    {"code": "activity", "name": "活动", "status": "active", "contract_version": 1},
                ],
            )
        await engine.dispose()

    asyncio.run(initialize())
    return TestClient(create_app(settings))


def product_payload(name: str = "黄铜书签") -> dict:
    return {
        "giftTypeCode": "product",
        "canonicalName": name,
        "recipientTypes": ["friend"],
        "occasions": ["birthday"],
        "priceMin": "39.00",
        "priceMax": "39.00",
        "whyTemplate": "送给喜欢阅读的人。",
        "verifiedAt": "2026-07-27T00:00:00Z",
        "productDetails": {
            "productForm": "physical",
            "genericProductName": "书签",
            "materials": ["黄铜"],
            "shippingRequired": True,
        },
    }


def login(client: TestClient) -> None:
    assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200


def test_gifts_require_the_existing_lightweight_session(tmp_path):
    """Catches routes that accidentally become public or add another auth mechanism."""
    with create_client(tmp_path) as client:
        response = client.post("/api/gifts", json=product_payload())

    assert response.status_code == 401


def test_create_list_duplicate_check_and_copy_gift(tmp_path):
    """Catches CRUD paths that miss duplicate blocking or leak verification to copies."""
    with create_client(tmp_path) as client:
        login(client)
        created = client.post("/api/gifts", json=product_payload())
        assert created.status_code == 201
        gift = created.json()
        assert gift["completenessScore"] == 100

        updated_payload = product_payload("黄铜书签升级版")
        updated = client.put(f"/api/gifts/{gift['id']}", json=updated_payload)
        assert updated.status_code == 200
        assert updated.json()["canonicalName"] == "黄铜书签升级版"
        assert client.get(f"/api/gifts/{gift['id']}").json()["canonicalName"] == "黄铜书签升级版"

        duplicate = client.post("/api/gifts", json=product_payload("  黄铜书签升级版  "))
        assert duplicate.status_code == 409

        warning = client.get("/api/gifts/duplicates", params={"canonicalName": "黄铜书签升级版X"})
        assert warning.status_code == 200
        assert warning.json()["matches"][0]["exact"] is False

        listed = client.get("/api/gifts", params={"giftType": "product", "minCompleteness": 100})
        assert listed.status_code == 200
        assert listed.json()["total"] == 1

        copied = client.post(f"/api/gifts/{gift['id']}/copy")
        assert copied.status_code == 201
        assert copied.json()["id"] != gift["id"]
        assert copied.json()["canonicalName"] == "黄铜书签升级版（副本）"
        assert copied.json()["verifiedAt"] is None


def test_duplicate_warnings_use_a_strict_trigram_threshold(tmp_path):
    """Catches sequence-based matching and a non-strict similarity cutoff."""
    with create_client(tmp_path) as client:
        login(client)
        assert client.post("/api/gifts", json=product_payload("abcdefg")).status_code == 201

        at_or_below_threshold = client.get(
            "/api/gifts/duplicates", params={"canonicalName": "abcdefX"}
        )
        assert at_or_below_threshold.status_code == 200
        assert at_or_below_threshold.json()["matches"] == []

        above_threshold = client.get(
            "/api/gifts/duplicates", params={"canonicalName": "abcdefgX"}
        )
        assert above_threshold.status_code == 200
        matches = above_threshold.json()["matches"]
        assert len(matches) == 1
        assert matches[0]["canonical_name"] == "abcdefg"
        assert matches[0]["similarity"] == 0.9091
        assert matches[0]["exact"] is False
