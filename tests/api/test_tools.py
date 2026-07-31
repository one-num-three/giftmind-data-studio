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
    assert response.json() == {"configured": True, "model": "deepseek-v4-flash"}
    assert "sk-preview-secret-12345" not in response.text
    assert status_response.status_code == 200
    assert status_response.json() == {"configured": True, "model": "deepseek-v4-flash"}
    assert "sk-preview-secret-12345" in env_path.read_text(encoding="utf-8")
    assert "sk-preview-secret-12345" not in status_response.text


def test_deepseek_suggest_returns_complete_product_prefill(tmp_path, monkeypatch):
    captured_request = {}

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
            captured_request.update(_kwargs)
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
    assert captured_request["json"]["model"] == "deepseek-v4-flash"


def test_taobao_login_panel_keeps_browser_state_server_side(tmp_path):
    class FakeTaobaoLogin:
        async def start(self):
            return {"sessionId": "11111111-1111-4111-8111-111111111111", "ready": False, "url": "https://login.taobao.com/", "cookieCount": 0, "stateSaved": False}

        async def status(self, _session_id):
            return {"sessionId": "11111111-1111-4111-8111-111111111111", "ready": True, "url": "https://www.taobao.com/", "cookieCount": 2, "stateSaved": False}

        async def screenshot(self, _session_id):
            return b"png-bytes"

        async def action(self, _session_id, _action, **_kwargs):
            return await self.status(_session_id)

        async def save(self, _session_id):
            result = await self.status(_session_id)
            result["stateSaved"] = True
            return result

        async def clear(self):
            return None

    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'giftmind.sqlite3').as_posix()}",
    )
    app = create_app(settings)
    app.state.taobao_login = FakeTaobaoLogin()
    with TestClient(app) as client:
        assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200
        started = client.post("/api/taobao/login")
        session_id = started.json()["sessionId"]
        assert started.status_code == 200
        assert client.get(f"/api/taobao/login/{session_id}/screenshot").content == b"png-bytes"
        assert client.post(f"/api/taobao/login/{session_id}/action", json={"action": "click", "x": 20, "y": 30}).json()["ready"] is True
        saved = client.post(f"/api/taobao/login/{session_id}/complete")

    assert saved.status_code == 200
    assert saved.json()["stateSaved"] is True
