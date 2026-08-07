"""Contract tests for the reserved H5 voice transcription endpoint."""
from backend.app.api.routes import voice as voice_route
from backend.app.core.config import Settings
from backend.app.services.asr_client import Transcription
from tests.api.test_gifts import create_client


def test_voice_transcribe_returns_501_when_unconfigured(tmp_path):
    with create_client(tmp_path) as client:
        status = client.get("/api/h5/voice/status")
        assert status.status_code == 200
        assert status.json()["configured"] is False
        response = client.post(
            "/api/h5/voice/transcribe",
            files={"audio": ("voice.webm", b"fake-audio-bytes", "audio/webm")},
            data={"format": "webm"},
        )

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "VOICE_NOT_CONFIGURED"


def test_voice_transcribe_configured_calls_provider(tmp_path, monkeypatch):
    async def fake_transcribe(settings, *, filename, content, content_type):
        assert isinstance(settings, Settings)
        assert content == b"fake-audio-bytes"
        return Transcription(
            transcript="我们第一次一起看极光",
            confidence=0.93,
            segments=[{"start": 0.0, "end": 2.5, "text": "我们第一次一起看极光"}],
            source="qwen-asr",
        )

    monkeypatch.setattr(voice_route, "transcribe_audio", fake_transcribe)
    with create_client(
        tmp_path,
        voice_asr_provider="qwen-asr",
        voice_asr_base_url="http://127.0.0.1:9999/v1",
        voice_asr_api_key="test-key",
    ) as client:
        response = client.post(
            "/api/h5/voice/transcribe",
            files={"audio": ("voice.webm", b"fake-audio-bytes", "audio/webm")},
            data={"format": "webm"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "我们第一次一起看极光"
    assert payload["confidence"] == 0.93
    assert payload["source"] == "qwen-asr"
    assert payload["segments"][0]["text"] == "我们第一次一起看极光"


def test_voice_transcribe_rejects_bad_format_and_empty_audio(tmp_path):
    with create_client(tmp_path) as client:
        bad_format = client.post(
            "/api/h5/voice/transcribe",
            files={"audio": ("voice.xyz", b"x", "audio/xyz")},
            data={"format": "xyz"},
        )
        assert bad_format.status_code == 422

        empty = client.post(
            "/api/h5/voice/transcribe",
            files={"audio": ("voice.webm", b"", "audio/webm")},
            data={"format": "webm"},
        )
        assert empty.status_code == 422
