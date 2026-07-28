import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_reports_schema_version(test_settings):
    with TestClient(create_app(test_settings)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schemaVersion": 1}


def test_app_module_rejects_missing_required_settings():
    environment = os.environ.copy()
    environment.pop("APP_SECRET", None)
    environment.pop("TEAM_PASSCODE", None)
    script = "from backend.app.main import app"

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ValidationError" in result.stderr
    assert "app_secret" in result.stderr
    assert "team_passcode" in result.stderr
