from backend.app.core.config import Settings
from backend.app.main import create_app
from fastapi.testclient import TestClient
from backend.app.api.routes import tools as tools_route


def create_tools_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'giftmind.sqlite3').as_posix()}",
    )
    return TestClient(create_app(settings))


def test_deepseek_status_requires_login_and_never_returns_key(tmp_path):
    with create_tools_client(tmp_path) as client:
        response = client.get("/api/settings/deepseek")

    assert response.status_code == 401


def test_deepseek_key_can_be_saved_to_env_without_echoing_it(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.chdir(tmp_path)
    with create_tools_client(tmp_path) as client:
        assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200
        response = client.put("/api/settings/deepseek", json={"apiKey": "sk-preview-secret-12345"})
        status_response = client.get("/api/settings/deepseek")

    assert response.status_code == 200
    assert response.json() == {"configured": True, "model": "deepseek-chat"}
    assert "sk-preview-secret-12345" not in response.text
    assert status_response.status_code == 200
    assert status_response.json() == {"configured": True, "model": "deepseek-chat"}
    assert "sk-preview-secret-12345" in env_path.read_text(encoding="utf-8")
    assert "sk-preview-secret-12345" not in status_response.text


def test_deepseek_suggest_returns_complete_product_prefill(tmp_path, monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": """```json
{
  "recommendedGiftTypeCode": "product",
  "subcategoryCode": "stationery",
  "shortDescription": "南京博物院主题金属书签。",
  "whyTemplate": "适合送给喜欢阅读和南京文化的朋友。",
  "priceMin": 39,
  "priceMax": 99,
  "recipientTypes": ["朋友"],
  "occasions": ["生日"],
  "interests": ["阅读", "旅行"],
  "tags": ["有仪式感", "小众"],
  "productDetails": {
    "genericProductName": "金属书签",
    "materials": ["金属"],
    "personalizationMethods": [],
    "shippingRequired": true
  }
}
```"""}}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-complete-prefill")
    monkeypatch.setattr(tools_route.httpx, "AsyncClient", lambda **_kwargs: FakeClient())
    tools_route.get_settings.cache_clear()
    try:
        with create_tools_client(tmp_path) as client:
            assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200
            response = client.post("/api/ai/suggest", json={"canonicalName": "南京博物院文创书签", "giftTypeCode": "product"})
    finally:
        tools_route.get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "deepseek"
    assert payload["priceMin"] == 39
    assert payload["priceMax"] == 99
    assert payload["whyTemplate"].startswith("适合送给")
    assert payload["recipientTypes"] == ["朋友"]
    assert payload["productDetails"]["materials"] == ["金属"]
