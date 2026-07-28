import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.main import create_app


def test_health_reports_schema_version(test_settings):
    with TestClient(create_app(test_settings)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schemaVersion": 1}


@pytest.mark.parametrize("missing_setting", ["APP_SECRET", "TEAM_PASSCODE"])
def test_app_module_rejects_each_missing_required_setting(missing_setting):
    environment = os.environ.copy()
    environment["APP_SECRET"] = "valid-secret"
    environment["TEAM_PASSCODE"] = "valid-passcode"
    environment.pop(missing_setting, None)
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
    assert missing_setting.lower() in result.stderr


@pytest.mark.parametrize(
    "field, value",
    [("app_secret", ""), ("app_secret", " \t"), ("team_passcode", ""), ("team_passcode", " \t")],
)
def test_settings_rejects_blank_required_secrets(field, value):
    values = {"app_secret": "valid-secret", "team_passcode": "valid-passcode"}
    values[field] = value

    with pytest.raises(ValidationError):
        Settings(**values)
