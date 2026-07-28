import asyncio
import base64
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.api.routes import assistant as assistant_route
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.taxonomy import GiftTypeDefinition


def create_assistant_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'assistant-api.sqlite3').as_posix()}",
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


def product_payload(name: str) -> dict:
    return {
        "giftTypeCode": "product",
        "canonicalName": name,
        "productDetails": {
            "productForm": "physical",
            "materials": [],
            "shippingRequired": False,
        },
    }


def test_thread_creation_is_idempotent_and_drafts_are_isolated(tmp_path):
    draft_a = "11111111-1111-4111-8111-111111111111"
    draft_b = "22222222-2222-4222-8222-222222222222"
    with create_assistant_client(tmp_path) as client:
        login(client)
        first = client.post("/api/ai/threads", json={"draftId": draft_a})
        repeated = client.post("/api/ai/threads", json={"draftId": draft_a})
        second = client.post("/api/ai/threads", json={"draftId": draft_b})
        assert first.status_code == 201
        assert repeated.status_code == 200
        assert first.json()["id"] == repeated.json()["id"]
        assert first.json()["id"] != second.json()["id"]

        first_message = client.post(
            f"/api/ai/threads/{first.json()['id']}/messages",
            json={"content": "黄铜书签，价格约 69 元", "giftTypeCode": "product", "currentValues": {}},
        )
        second_message = client.post(
            f"/api/ai/threads/{second.json()['id']}/messages",
            json={"content": "双人陶艺体验", "giftTypeCode": "activity", "currentValues": {}},
        )
        assert first_message.status_code == 201
        assert second_message.status_code == 201

        first_reloaded = client.get(f"/api/ai/threads/{first.json()['id']}").json()
        second_reloaded = client.get(f"/api/ai/threads/{second.json()['id']}").json()

    assert [message["content"] for message in first_reloaded["messages"] if message["role"] == "user"] == [
        "黄铜书签，价格约 69 元"
    ]
    assert [message["content"] for message in second_reloaded["messages"] if message["role"] == "user"] == [
        "双人陶艺体验"
    ]
    assert first_message.json()["suggestionRun"]["patches"]
    assert first_message.json()["suggestionRun"]["source"] == "rule"


def test_message_extracts_link_without_failing_when_the_page_is_unavailable(tmp_path, monkeypatch):
    extracted = AsyncMock(
        return_value={
            "url": "https://example.com/gift",
            "label": "商品详情",
            "status": "ok",
            "title": "黄铜书签",
            "description": "可刻字",
            "text": "礼盒价 69 元",
            "structuredData": [],
            "priceHints": ["69"],
        }
    )
    monkeypatch.setattr(assistant_route, "extract_public_page", extracted)
    with create_assistant_client(tmp_path) as client:
        login(client)
        thread = client.post(
            "/api/ai/threads",
            json={"draftId": "33333333-3333-4333-8333-333333333333"},
        ).json()
        response = client.post(
            f"/api/ai/threads/{thread['id']}/messages",
            json={
                "content": "看看这个 https://example.com/gift",
                "giftTypeCode": "product",
                "currentValues": {},
            },
        )

    assert response.status_code == 201
    assert response.json()["sourceRefs"][0]["label"] == "商品详情"
    extracted.assert_awaited_once()


def test_review_state_and_gift_binding_are_persisted(tmp_path):
    with create_assistant_client(tmp_path) as client:
        login(client)
        thread = client.post(
            "/api/ai/threads",
            json={"draftId": "44444444-4444-4444-8444-444444444444"},
        ).json()
        turn = client.post(
            f"/api/ai/threads/{thread['id']}/messages",
            json={"content": "黄铜书签", "giftTypeCode": "product", "currentValues": {}},
        ).json()
        run_id = turn["suggestionRun"]["id"]
        review = client.patch(
            f"/api/ai/suggestion-runs/{run_id}",
            json={"appliedFields": ["shortDescription"], "ignoredFields": ["whyTemplate"]},
        )
        gift = client.post("/api/gifts", json=product_payload("绑定测试礼物")).json()
        bind = client.patch(
            f"/api/ai/threads/{thread['id']}/bind",
            json={"giftId": gift["id"]},
        )
        missing = client.patch(
            f"/api/ai/threads/{thread['id']}/bind",
            json={"giftId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
        )
        reloaded = client.get(f"/api/ai/threads/{thread['id']}").json()

    assert review.status_code == 200
    assert review.json()["appliedFields"] == ["shortDescription"]
    assert review.json()["ignoredFields"] == ["whyTemplate"]
    assert bind.status_code == 200
    assert bind.json()["giftId"] == gift["id"]
    assert missing.status_code == 404
    assert reloaded["giftId"] == gift["id"]


def test_image_attachment_is_uploaded_and_sent_with_the_message(tmp_path, monkeypatch):
    generated = AsyncMock(return_value={"content": "已识别图片。", "patches": [], "confidence": 0.8, "source": "deepseek"})
    monkeypatch.setattr(assistant_route, "generate_assistant_result", generated)
    with create_assistant_client(tmp_path) as client:
        login(client)
        thread = client.post("/api/ai/threads", json={"draftId": "55555555-5555-4555-8555-555555555555"}).json()
        uploaded = client.post(
            f"/api/ai/threads/{thread['id']}/attachments",
            files={"file": ("gift.png", base64.b64decode("iVBORw0KGgo="), "image/png")},
        )
        assert uploaded.status_code == 201
        attachment = uploaded.json()
        response = client.post(
            f"/api/ai/threads/{thread['id']}/messages",
            json={"content": "请识别图片", "giftTypeCode": "product", "currentValues": {}, "attachments": [attachment]},
        )

    assert response.status_code == 201
    assert response.json()["userMessage"]["attachments"][0]["name"] == "gift.png"
    assert generated.await_args.kwargs["image_attachments"][0]["data"].startswith("data:image/png;base64,")


def test_assistant_rejects_unsupported_or_oversized_images(tmp_path):
    with create_assistant_client(tmp_path) as client:
        login(client)
        thread = client.post("/api/ai/threads", json={"draftId": "66666666-6666-4666-8666-666666666666"}).json()
        unsupported = client.post(
            f"/api/ai/threads/{thread['id']}/attachments",
            files={"file": ("gift.gif", b"gif", "image/gif")},
        )
        oversized = client.post(
            f"/api/ai/threads/{thread['id']}/attachments",
            files={"file": ("huge.jpg", b"x" * (8 * 1024 * 1024 + 1), "image/jpeg")},
        )

    assert unsupported.status_code == 415
    assert oversized.status_code == 413
