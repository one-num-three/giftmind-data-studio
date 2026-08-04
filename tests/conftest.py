import os

from backend.app.core.config import Settings


os.environ.setdefault("APP_SECRET", "test-app-secret")
os.environ.setdefault("TEAM_PASSCODE", "test-team-passcode")
# Tests must never inherit a developer's real local provider key from `.env`.
# Individual AI client tests pass an explicit fake key when they need one.
os.environ["DEEPSEEK_API_KEY"] = ""


def pytest_configure() -> None:
    """Provide non-secret settings before test modules import the app."""


import pytest


@pytest.fixture
def test_settings() -> Settings:
    return Settings(app_secret="test-app-secret", team_passcode="test-team-passcode")
