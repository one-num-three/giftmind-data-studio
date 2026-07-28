from datetime import UTC, datetime

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def create_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode_hash=PasswordHasher().hash("team-secret"),
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'giftmind.sqlite3').as_posix()}",
    )
    return TestClient(create_app(settings))


def test_login_sets_http_only_lax_cookie_and_returns_session_details(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post("/api/session/login", json={"passcode": "team-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["csrfToken"]
    assert datetime.fromisoformat(body["expiresAt"]).tzinfo is not None
    assert "giftmind_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]


def test_login_cookie_is_secure_for_https_requests(tmp_path):
    with create_client(tmp_path) as client:
        response = client.post(
            "/api/session/login",
            json={"passcode": "team-secret"},
            headers={"X-Forwarded-Proto": "https"},
        )

    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_sixth_bad_login_from_one_ip_is_rate_limited(tmp_path):
    with create_client(tmp_path) as client:
        for _ in range(5):
            response = client.post("/api/session/login", json={"passcode": "wrong"})
            assert response.status_code == 401
        response = client.post("/api/session/login", json={"passcode": "wrong"})

    assert response.status_code == 429


def test_login_from_another_ip_is_not_blocked_by_failed_attempts(tmp_path):
    with create_client(tmp_path) as client:
        for _ in range(5):
            client.post("/api/session/login", json={"passcode": "wrong"})
        response = client.post(
            "/api/session/login",
            json={"passcode": "team-secret"},
            headers={"X-Forwarded-For": "203.0.113.9"},
        )

    assert response.status_code == 200


def test_logout_revokes_session_and_clears_cookie(tmp_path):
    with create_client(tmp_path) as client:
        login = client.post("/api/session/login", json={"passcode": "team-secret"})
        csrf_token = login.json()["csrfToken"]
        logout = client.post("/api/session/logout", headers={"X-CSRF-Token": csrf_token})
        session = client.get("/api/session")

    assert logout.status_code == 204
    assert "giftmind_session=\"\"" in logout.headers["set-cookie"]
    assert session.status_code == 401


def test_current_session_requires_a_valid_cookie(tmp_path):
    with create_client(tmp_path) as client:
        response = client.get("/api/session")

    assert response.status_code == 401
