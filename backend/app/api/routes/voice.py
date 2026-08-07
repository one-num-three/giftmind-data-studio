"""Reserved H5 voice input endpoint (recording → transcript → chat pipeline)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from backend.app.services.asr_client import (
    AsrNotConfiguredError,
    AsrProviderError,
    asr_configured,
    transcribe_audio,
)

router = APIRouter(prefix="/api/h5/voice", tags=["h5-voice"])

SUPPORTED_FORMATS = {"webm", "wav", "mp3", "m4a", "ogg", "opus"}
MAX_AUDIO_BYTES = 8 * 1024 * 1024


@router.get("/status")
async def voice_status(request: Request) -> dict[str, object]:
    return {"configured": asr_configured(request.app.state.settings)}


@router.post("/transcribe")
async def transcribe(
    request: Request,
    audio: Annotated[UploadFile, File()],
    format: Annotated[Literal["webm", "wav", "mp3", "m4a", "ogg", "opus"], Form()],
) -> dict[str, object]:
    """Transcribe a short audio clip; callers must handle VOICE_NOT_CONFIGURED."""
    settings = request.app.state.settings
    content = await audio.read(MAX_AUDIO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="音频文件为空")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="单段音频不能超过 8MB")
    if not asr_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "VOICE_NOT_CONFIGURED",
                "message": "语音转写服务未配置，请在服务器 .env 填写 VOICE_ASR_* 配置",
            },
        )
    filename = audio.filename or f"voice.{format}"
    try:
        result = await transcribe_audio(
            settings,
            filename=filename,
            content=content,
            content_type=audio.content_type or "application/octet-stream",
        )
    except AsrNotConfiguredError as exc:
        raise HTTPException(status_code=501, detail={"code": "VOICE_NOT_CONFIGURED", "message": str(exc)}) from exc
    except AsrProviderError as exc:
        raise HTTPException(status_code=502, detail={"code": "VOICE_PROVIDER_ERROR", "message": str(exc)}) from exc
    return {
        "transcript": result.transcript,
        "confidence": result.confidence,
        "segments": result.segments or [],
        "source": result.source,
    }
