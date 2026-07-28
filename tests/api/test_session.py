from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.api.deps import SessionContext, require_session
from backend.app.core.config import Settings
from backend.app.core.security import create_session_token
from backend.app.main import create_app


def create_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode="team-secret",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'giftmind.sqlite3').as_posix()}",
    )
    app: FastAPI = create_app(settings)

    @app.get("/api/test/protected")
    async def protected_endpoint(session: SessionContext = Depends(require_session)) -> dict[str, bool]:
        return {"ok": session.authenticated}

    return TestClient(app)


def test_login_sets_strict_http_only_cookie_and_session_status(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post("/api/session/login", json={"passcode": "team-secret"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert datetime.fromisoformat(response.json()["expiresAt"]).tzinfo is not None
    assert "giftmind_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Max-Age=604800" in response.headers["set-cookie"]


def test_wrong_passcode_is_rejected(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post("/api/session/login", json={"passcode": "wrong"})

    assert response.status_code == 401


def test_login_cookie_is_secure_for_https_requests(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post(
            "/api/session/login",
            json={"passcode": "team-secret"},
            headers={"X-Forwarded-Proto": "https"},
        )

    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_logout_clears_cookie_without_server_state(tmp_path):
    with create_client(tmp_path) as client:
        assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200
        logout = client.post("/api/session/logout")
        session = client.get("/api/session")

    assert logout.status_code == 204
    assert "giftmind_session=\"\"" in logout.headers["set-cookie"]
    assert "SameSite=strict" in logout.headers["set-cookie"]
    assert session.status_code == 401


def test_protected_route_rejects_missing_and_malformed_cookies(tmp_path):
    with create_client(tmp_path) as client:
        missing = client.get("/api/test/protected")
        client.cookies.set("giftmind_session", "malformed")
        malformed = client.get("/api/test/protected")

    assert missing.status_code == 401
    assert malformed.status_code == 401


def test_protected_route_rejects_expired_cookie(tmp_path):
    with create_client(tmp_path) as client:
        expired = create_session_token(
            session_id=uuid4(),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            secret="test-app-secret",
        )
        client.cookies.set("giftmind_session", expired)
        response = client.get("/api/test/protected")

    assert response.status_code == 401


def test_session_status_accepts_valid_cookie(tmp_path):
    with create_client(tmp_path) as client:
        assert client.post("/api/session/login", json={"passcode": "team-secret"}).status_code == 200
        response = client.get("/api/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
