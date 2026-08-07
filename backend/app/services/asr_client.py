"""Provider-agnostic speech-to-text client for H5 voice input."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.core.config import Settings


class AsrNotConfiguredError(RuntimeError):
    """Raised when no ASR provider has been configured in the environment."""


class AsrProviderError(RuntimeError):
    """Raised when the configured ASR provider returns an error."""


@dataclass(frozen=True)
class Transcription:
    transcript: str
    confidence: float | None = None
    segments: list[dict] | None = None
    source: str = "asr"


def asr_configured(settings: Settings) -> bool:
    return bool(
        settings.voice_asr_provider.strip()
        and settings.voice_asr_base_url.strip()
        and settings.voice_asr_api_key
    )


async def transcribe_audio(
    settings: Settings,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> Transcription:
    """Transcribe one audio upload through an OpenAI-compatible endpoint."""
    if not asr_configured(settings):
        raise AsrNotConfiguredError("voice_asr_provider is not configured")
    base_url = settings.voice_asr_base_url.rstrip("/")
    model = settings.voice_asr_model.strip() or "whisper-1"
    files = {
        "file": (filename, content, content_type or "application/octet-stream"),
        "model": (None, model),
        "response_format": (None, "verbose_json"),
    }
    headers = {"Authorization": f"Bearer {settings.voice_asr_api_key}"}
    timeout = httpx.Timeout(60.0, connect=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/audio/transcriptions",
                files=files,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise AsrProviderError(f"ASR 服务连接失败：{exc.__class__.__name__}") from exc
    if response.status_code >= 400:
        raise AsrProviderError(f"ASR 服务返回 {response.status_code}")
    data = response.json()
    transcript = str(data.get("text") or "").strip()
    if not transcript:
        raise AsrProviderError("ASR 服务返回了空的转写结果")
    segments = [
        {
            "start": float(segment.get("start") or 0),
            "end": float(segment.get("end") or 0),
            "text": str(segment.get("text") or "").strip(),
        }
        for segment in data.get("segments") or []
        if segment.get("text")
    ]
    return Transcription(
        transcript=transcript,
        confidence=_confidence(data),
        segments=segments or None,
        source=settings.voice_asr_provider.strip(),
    )


def _confidence(data: dict) -> float | None:
    value = data.get("confidence")
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, confidence))
