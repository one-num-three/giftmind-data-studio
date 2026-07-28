from backend.app.core.config import Settings
from backend.app.main import create_app
from fastapi.testclient import TestClient


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
