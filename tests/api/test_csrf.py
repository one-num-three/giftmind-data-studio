from argon2 import PasswordHasher
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.api.deps import SessionContext, require_csrf, require_session
from backend.app.core.config import Settings
from backend.app.main import create_app


def create_client(tmp_path) -> TestClient:
    settings = Settings(
        app_secret="test-app-secret",
        team_passcode_hash=PasswordHasher().hash("team-secret"),
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'giftmind.sqlite3').as_posix()}",
    )
    app: FastAPI = create_app(settings)

    @app.post("/api/test/protected")
    async def protected_endpoint(
        session: SessionContext = Depends(require_session),
        _: None = Depends(require_csrf),
    ) -> dict[str, bool]:
        return {"ok": session.authenticated}

    return TestClient(app)


def test_protected_post_rejects_missing_csrf_token(tmp_path):
    with create_client(tmp_path) as client:
        client.post("/api/session/login", json={"passcode": "team-secret"})
        response = client.post("/api/test/protected")

    assert response.status_code == 403


def test_protected_post_rejects_wrong_csrf_token(tmp_path):
    with create_client(tmp_path) as client:
        client.post("/api/session/login", json={"passcode": "team-secret"})
        response = client.post("/api/test/protected", headers={"X-CSRF-Token": "wrong"})

    assert response.status_code == 403


def test_protected_post_accepts_session_csrf_token(tmp_path):
    with create_client(tmp_path) as client:
        login = client.post("/api/session/login", json={"passcode": "team-secret"})
        response = client.post(
            "/api/test/protected",
            headers={"X-CSRF-Token": login.json()["csrfToken"]},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
