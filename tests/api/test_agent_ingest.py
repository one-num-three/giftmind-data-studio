"""End-to-end contract for one-call Agent gift ingestion."""

import asyncio
import hashlib
import io
import json
import zipfile
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.api.routes import agent_ingest as agent_route
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.taxonomy import GiftTypeDefinition


def create_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'agent-ingest.sqlite3').as_posix()}",
        data_dir=tmp_path / "data",
        upload_dir=tmp_path / "uploads",
        backup_dir=tmp_path / "backups",
        deepseek_api_key=None,
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


def login(client: TestClient) -> None:
    assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200


def test_agent_ingest_requires_existing_team_session(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post("/api/agent/gifts/ingest", data={"description": "黄铜书签"})

    assert response.status_code == 401


def test_agent_skill_metadata_and_download_are_public(tmp_path):
    with create_client(tmp_path) as client:
        metadata = client.get("/api/agent/skill")
        download = client.get("/api/agent/skill/download")

    assert metadata.status_code == 200
    assert metadata.json()["name"] == "giftmind-gift-ingest"
    assert metadata.json()["downloadUrl"].endswith("/api/agent/skill/download")
    assert metadata.json()["sha256"] == hashlib.sha256(download.content).hexdigest()
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    assert "giftmind-gift-ingest-1.1.0.zip" in download.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        names = set(archive.namelist())
    assert "giftmind-gift-ingest/SKILL.md" in names
    assert "giftmind-gift-ingest/scripts/ingest_gift.py" in names


def test_agent_ingest_analyzes_and_creates_product_draft(tmp_path):
    known = {
        "canonicalName": "东南大学校徽黄铜书签",
        "productDetails": {"colors": ["黄铜色"]},
        "collectorNotes": "首批人工采集",
    }
    with create_client(tmp_path) as client:
        login(client)
        response = client.post(
            "/api/agent/gifts/ingest",
            data={
                "description": "东南大学校徽黄铜书签，价格 39-59 元，适合作为毕业纪念。",
                "known_fields_json": json.dumps(known, ensure_ascii=False),
            },
        )
        listing = client.get("/api/gifts")

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["created"] is True
    assert payload["gift"]["canonicalName"] == "东南大学校徽黄铜书签"
    assert payload["gift"]["giftTypeCode"] == "product"
    assert payload["gift"]["status"] == "draft"
    assert float(payload["gift"]["priceMin"]) == 39
    assert float(payload["gift"]["priceMax"]) == 59
    assert payload["gift"]["productDetails"]["colors"] == ["黄铜色"]
    assert payload["analysis"]["source"] == "rule"
    assert listing.json()["total"] == 1


def test_agent_ingest_auto_detects_shared_activity(tmp_path):
    known = {
        "canonicalName": "双人陶艺纪念体验",
        "activityDetails": {
            "durationMinutesMin": 90,
            "durationMinutesMax": 120,
            "participantsMin": 2,
            "participantsMax": 2,
            "pricingUnit": "双人",
        },
    }
    with create_client(tmp_path) as client:
        login(client)
        response = client.post(
            "/api/agent/gifts/ingest",
            data={
                "description": "和女朋友一起参加的双人陶艺活动，价格 299 元，需要预约。",
                "known_fields_json": json.dumps(known, ensure_ascii=False),
            },
        )

    assert response.status_code == 201, response.text
    gift = response.json()["gift"]
    assert gift["giftTypeCode"] == "activity"
    assert gift["activityDetails"]["activityMode"] == "offline"
    assert gift["productDetails"] is None


def test_agent_ingest_understands_and_stores_uploaded_image(tmp_path, monkeypatch):
    understood = AsyncMock(
        return_value=[
            {
                "label": "图片：bookmark.png",
                "status": "ok",
                "text": "OCR 文字：南京博物院 金属书签",
                "processor": "paddleocr",
            }
        ]
    )
    monkeypatch.setattr(agent_route, "understand_images", understood)
    with create_client(tmp_path) as client:
        login(client)
        response = client.post(
            "/api/agent/gifts/ingest",
            data={"known_fields_json": json.dumps({"canonicalName": "南京博物院金属书签"}, ensure_ascii=False)},
            files=[("images", ("bookmark.png", b"not-a-real-png", "image/png"))],
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["images"][0]["isCover"] is True
    assert payload["images"][0]["url"].startswith("/uploads/gifts/")
    assert payload["analysis"]["sourceRefs"][0]["processor"] == "paddleocr"
    assert understood.await_count == 1


def test_agent_ingest_local_mode_skips_cloud_analysis(tmp_path, monkeypatch):
    cloud_analysis = AsyncMock()
    source_collection = AsyncMock()
    monkeypatch.setattr(agent_route, "generate_assistant_result", cloud_analysis)
    monkeypatch.setattr(agent_route, "_collect_sources", source_collection)
    known = {
        "canonicalName": "本地分析礼物",
        "shortDescription": "由本地 Agent 根据用户材料完成的结构化礼物草稿。",
        "giftTypeCode": "product",
        "recipientTypes": ["朋友"],
        "occasions": ["生日"],
        "tags": ["实用礼物"],
        "confidenceLevel": "high",
        "productDetails": {
            "productForm": "physical",
            "genericProductName": "杯子礼盒",
            "colors": ["蓝色"],
            "shippingRequired": True,
        },
    }
    with create_client(tmp_path) as client:
        login(client)
        response = client.post(
            "/api/agent/gifts/ingest",
            data={
                "analysis_mode": "local",
                "description": "本地 Agent 已完成图片和商品信息分析。",
                "source_urls_json": json.dumps(["https://example.com/gift"]),
                "known_fields_json": json.dumps(known, ensure_ascii=False),
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["gift"]["canonicalName"] == "本地分析礼物"
    assert payload["gift"]["recipientTypes"] == ["朋友"]
    assert payload["analysis"]["mode"] == "local"
    assert payload["analysis"]["source"] == "local-agent"
    assert payload["analysis"]["suggestedFieldCount"] == 0
    assert payload["analysis"]["sourceRefs"][0]["processor"] == "local-agent"
    assert cloud_analysis.await_count == 0
    assert source_collection.await_count == 0


def test_agent_ingest_blocks_exact_duplicates(tmp_path):
    data = {
        "description": "黄铜书签，价格 69 元。",
        "known_fields_json": json.dumps({"canonicalName": "重复礼物"}, ensure_ascii=False),
    }
    with create_client(tmp_path) as client:
        login(client)
        first = client.post("/api/agent/gifts/ingest", data=data)
        duplicate = client.post("/api/agent/gifts/ingest", data=data)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DUPLICATE_GIFT"


def test_agent_counts_products_activities_and_statuses(tmp_path):
    with create_client(tmp_path) as client:
        login(client)
        empty = client.get("/api/agent/gifts/counts")
        product = client.post(
            "/api/agent/gifts/ingest",
            data={
                "known_fields_json": json.dumps({"canonicalName": "统计商品"}, ensure_ascii=False),
                "description": "统计用黄铜书签，价格 49 元。",
            },
        )
        activity = client.post(
            "/api/agent/gifts/ingest",
            data={
                "gift_type_code": "activity",
                "lifecycle_status": "active",
                "known_fields_json": json.dumps({"canonicalName": "统计活动"}, ensure_ascii=False),
                "description": "和家人一起参加的双人陶艺活动，价格 299 元。",
            },
        )
        counts = client.get("/api/agent/gifts/counts")

    assert empty.json() == {
        "productCount": 0,
        "activityCount": 0,
        "totalCount": 0,
        "byStatus": {"draft": 0, "active": 0, "inactive": 0},
    }
    assert product.status_code == 201
    assert activity.status_code == 201
    assert counts.json() == {
        "productCount": 1,
        "activityCount": 1,
        "totalCount": 2,
        "byStatus": {"draft": 1, "active": 1, "inactive": 0},
    }
