"""Persistent AI selection-assistant conversations and human review state."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import SessionContext, get_db_session, require_session
from backend.app.models.assistant import AIMessage, AISuggestionRun, AIThread
from backend.app.models.gift import Gift
from backend.app.schemas.common import APIModel
from backend.app.services.assistant_suggestions import generate_assistant_result
from backend.app.services.source_extraction import extract_public_page, extract_urls


router = APIRouter(prefix="/api/ai", tags=["assistant"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
ProtectedSession = Annotated[SessionContext, Depends(require_session)]


class ThreadInput(APIModel):
    draft_id: UUID
    gift_id: UUID | None = None


class MessageInput(APIModel):
    content: Annotated[str, Field(max_length=8000)] = ""
    gift_type_code: str = "product"
    current_values: dict[str, object] = Field(default_factory=dict)
    attachments: list[dict[str, str]] = Field(default_factory=list, max_length=4)


class ReviewInput(APIModel):
    applied_fields: list[str] = Field(default_factory=list)
    ignored_fields: list[str] = Field(default_factory=list)


class BindInput(APIModel):
    gift_id: UUID


def _message_dict(message: AIMessage) -> dict[str, object]:
    return {
        "id": message.id,
        "threadId": message.thread_id,
        "role": message.role,
        "content": message.content,
        "attachments": message.attachments_json,
        "sourceRefs": message.source_refs_json,
        "createdAt": message.created_at,
    }


def _run_dict(run: AISuggestionRun) -> dict[str, object]:
    applied = set(run.applied_fields or [])
    ignored = set(run.ignored_fields or [])
    patches: list[dict[str, object]] = []
    for stored in run.patch_json or []:
        patch = dict(stored)
        path = str(patch.get("path") or "")
        patch["status"] = "applied" if path in applied else "ignored" if path in ignored else "pending"
        patches.append(patch)
    return {
        "id": run.id,
        "threadId": run.thread_id,
        "assistantMessageId": run.assistant_message_id,
        "patches": patches,
        "confidence": run.confidence,
        "source": run.source,
        "sourceRefs": run.source_refs_json,
        "appliedFields": run.applied_fields,
        "ignoredFields": run.ignored_fields,
        "createdAt": run.created_at,
        "updatedAt": run.updated_at,
    }


async def _thread_or_404(session: AsyncSession, thread_id: UUID) -> AIThread:
    thread = (
        await session.execute(select(AIThread).where(AIThread.id == str(thread_id)))
    ).scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="AI thread not found")
    return thread


async def _thread_dict(session: AsyncSession, thread: AIThread) -> dict[str, object]:
    messages = (
        await session.execute(
            select(AIMessage)
            .where(AIMessage.thread_id == thread.id)
            .order_by(AIMessage.created_at, AIMessage.id)
        )
    ).scalars().all()
    runs = (
        await session.execute(
            select(AISuggestionRun)
            .where(AISuggestionRun.thread_id == thread.id)
            .order_by(AISuggestionRun.created_at, AISuggestionRun.id)
        )
    ).scalars().all()
    return {
        "id": thread.id,
        "draftId": thread.draft_id,
        "giftId": thread.gift_id,
        "status": thread.status,
        "createdAt": thread.created_at,
        "updatedAt": thread.updated_at,
        "messages": [_message_dict(message) for message in messages],
        "suggestionRuns": [_run_dict(run) for run in runs],
    }


@router.post("/threads")
async def create_or_restore_thread(
    payload: ThreadInput,
    response: Response,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> dict[str, object]:
    draft_id = str(payload.draft_id)
    thread = (
        await session.execute(select(AIThread).where(AIThread.draft_id == draft_id))
    ).scalar_one_or_none()
    if thread is None:
        thread = AIThread(draft_id=draft_id, gift_id=str(payload.gift_id) if payload.gift_id else None)
        session.add(thread)
        await session.commit()
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return await _thread_dict(session, thread)


@router.get("/threads/{thread_id}")
async def read_thread(
    thread_id: UUID,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> dict[str, object]:
    return await _thread_dict(session, await _thread_or_404(session, thread_id))


@router.post("/threads/{thread_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    thread_id: UUID,
    request: Request,
    session: DatabaseSession,
    _auth: ProtectedSession,
    file: UploadFile = File(...),
) -> dict[str, str]:
    thread = await _thread_or_404(session, thread_id)
    mime_type = file.content_type or ""
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、WebP 图片")
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单张图片不能超过 8MB")
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime_type]
    stored_name = f"{hashlib.sha256(content).hexdigest()}{suffix}"
    relative = Path("assistant") / thread.id / stored_name
    destination = request.app.state.settings.upload_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return {
        "id": stored_name,
        "name": Path(file.filename or f"image{suffix}").name,
        "mimeType": mime_type,
        "url": f"/uploads/{relative.as_posix()}",
    }


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    thread_id: UUID,
    payload: MessageInput,
    request: Request,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> dict[str, object]:
    thread = await _thread_or_404(session, thread_id)
    content = payload.content.strip()
    if not content and not payload.attachments:
        raise HTTPException(status_code=422, detail="请输入文字或添加图片")
    image_attachments: list[dict[str, str]] = []
    safe_attachments: list[dict[str, str]] = []
    expected_prefix = f"/uploads/assistant/{thread.id}/"
    for attachment in payload.attachments:
        url = str(attachment.get("url") or "")
        mime_type = str(attachment.get("mimeType") or "")
        if not url.startswith(expected_prefix) or mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=422, detail="图片附件无效")
        filename = Path(url).name
        local_path = request.app.state.settings.upload_dir / "assistant" / thread.id / filename
        if not local_path.is_file():
            raise HTTPException(status_code=422, detail="图片附件不存在")
        encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
        safe = {"id": filename, "name": Path(str(attachment.get("name") or filename)).name, "mimeType": mime_type, "url": url}
        safe_attachments.append(safe)
        image_attachments.append({"mimeType": mime_type, "data": f"data:{mime_type};base64,{encoded}"})
    user_message = AIMessage(
        thread_id=thread.id,
        role="user",
        content=content or "请识别我上传的礼物图片。",
        attachments_json=safe_attachments,
    )
    session.add(user_message)
    await session.flush()

    source_refs: list[dict[str, object]] = []
    urls = extract_urls(content)
    if urls:
        async with httpx.AsyncClient() as client:
            for url in urls:
                source_refs.append(await extract_public_page(url, client))
    if not source_refs:
        source_refs = [{"label": "用户描述", "status": "ok"}]
    user_message.source_refs_json = source_refs

    messages = (
        await session.execute(
            select(AIMessage)
            .where(AIMessage.thread_id == thread.id)
            .order_by(AIMessage.created_at, AIMessage.id)
        )
    ).scalars().all()
    history = [{"role": message.role, "content": message.content} for message in messages[-12:]]
    result = await generate_assistant_result(
        content=content,
        gift_type_code=payload.gift_type_code if payload.gift_type_code in {"product", "activity"} else "product",
        current_values=payload.current_values,
        history=history,
        source_refs=source_refs,
        image_attachments=image_attachments,
        api_key=request.app.state.settings.deepseek_api_key,
    )
    assistant_message = AIMessage(
        thread_id=thread.id,
        role="assistant",
        content=str(result["content"]),
        source_refs_json=source_refs,
    )
    session.add(assistant_message)
    await session.flush()
    run = AISuggestionRun(
        thread_id=thread.id,
        assistant_message_id=assistant_message.id,
        patch_json=result["patches"],
        confidence=float(result["confidence"]),
        source=str(result["source"]),
        source_refs_json=source_refs,
    )
    session.add(run)
    await session.commit()
    return {
        "userMessage": _message_dict(user_message),
        "assistantMessage": _message_dict(assistant_message),
        "suggestionRun": _run_dict(run),
        "sourceRefs": source_refs,
    }


@router.patch("/suggestion-runs/{run_id}")
async def review_suggestion_run(
    run_id: UUID,
    payload: ReviewInput,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> dict[str, object]:
    run = (
        await session.execute(select(AISuggestionRun).where(AISuggestionRun.id == str(run_id)))
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Suggestion run not found")
    valid_paths = {str(item.get("path")) for item in run.patch_json if isinstance(item, dict)}
    applied = [path for path in dict.fromkeys(payload.applied_fields) if path in valid_paths]
    ignored = [
        path
        for path in dict.fromkeys(payload.ignored_fields)
        if path in valid_paths and path not in applied
    ]
    run.applied_fields = applied
    run.ignored_fields = ignored
    await session.commit()
    return _run_dict(run)


@router.patch("/threads/{thread_id}/bind")
async def bind_thread_to_gift(
    thread_id: UUID,
    payload: BindInput,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> dict[str, object]:
    thread = await _thread_or_404(session, thread_id)
    gift_id = str(payload.gift_id)
    gift = (await session.execute(select(Gift.id).where(Gift.id == gift_id))).scalar_one_or_none()
    if gift is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    thread.gift_id = gift_id
    await session.commit()
    return await _thread_dict(session, thread)
