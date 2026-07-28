import os

from backend.app.core.config import Settings


os.environ.setdefault("APP_SECRET", "test-app-secret")
os.environ.setdefault("TEAM_PASSCODE", "test-team-passcode")


def pytest_configure() -> None:
    """Provide non-secret settings before test modules import the app."""


import pytest


@pytest.fixture
def test_settings() -> Settings:
    return Settings(app_secret="test-app-secret", team_passcode="test-team-passcode")
