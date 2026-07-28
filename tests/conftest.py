import os

from backend.app.core.config import Settings


os.environ.setdefault("APP_SECRET", "")
os.environ.setdefault("TEAM_PASSCODE_HASH", "")


def pytest_configure() -> None:
    """Provide non-secret settings before test modules import the app."""


import pytest


@pytest.fixture
def test_settings() -> Settings:
    return Settings(app_secret="", team_passcode_hash="")
