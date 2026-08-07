"""Public H5 share snapshots and recipient replies."""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db_session
from backend.app.models.shares import Share, ShareReply
from backend.app.schemas.common import APIModel, normalize_text

router = APIRouter(prefix="/api/h5/shares", tags=["h5-shares"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


class ShareUpsertRequest(APIModel):
    plan: dict[str, Any]
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("plan")
    @classmethod
    def require_shareable_plan(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value.get("gifts"), list) or not value["gifts"]:
            raise ValueError("plan.gifts must be a non-empty list")
        if not isinstance(value.get("letter"), dict):
            raise ValueError("plan.letter must be an object")  # noqa: TRY004
        if not isinstance(value.get("ritual"), list):
            raise ValueError("plan.ritual must be a list")  # noqa: TRY004
        return value


class ShareReplyRequest(APIModel):
    content: Annotated[str, Field(min_length=1, max_length=300)]
    reaction: Annotated[str | None, Field(max_length=32)] = None

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        cleaned = normalize_text(value)
        if not cleaned:
            raise ValueError("请写一句话")
        return cleaned

    @field_validator("reaction")
    @classmethod
    def clean_reaction(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None


def _record(share: Share) -> dict[str, Any]:
    return {
        "shareId": share.id,
        "slug": share.slug,
        "planId": share.plan_id,
        "plan": share.plan_json,
        "config": share.config_json,
        "createdAt": share.created_at.isoformat(),
        "updatedAt": share.updated_at.isoformat(),
    }


def _recipient_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Recipient-safe projection: never expose prices, scores, or the interview."""
    gifts = []
    for gift in plan.get("gifts") or []:
        if not isinstance(gift, Mapping):
            continue
        gifts.append(
            {
                key: gift.get(key)
                for key in ("name", "emoji", "why", "category")
                if gift.get(key) not in (None, "")
            }
        )
    return {
        key: plan.get(key)
        for key in ("schemaVersion", "title", "subtitle", "insight", "letter", "ritual", "share")
        if plan.get(key) is not None
    } | {"gifts": gifts}


async def _load_share(session: AsyncSession, share_id: str) -> Share:
    share = await session.get(Share, share_id)
    if share is None or share.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享内容不存在或已失效")
    return share


def _new_slug() -> str:
    return secrets.token_hex(6)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_share(payload: ShareUpsertRequest, session: DatabaseSession) -> dict[str, Any]:
    slug = _new_slug()
    share = Share(
        slug=slug,
        plan_id=str(payload.plan.get("id") or None)[:128] or None,
        plan_json=payload.plan,
        config_json=payload.config,
    )
    session.add(share)
    await session.commit()
    await session.refresh(share)
    return _record(share)


@router.put("/{share_id}")
async def update_share(
    share_id: str, payload: ShareUpsertRequest, session: DatabaseSession
) -> dict[str, Any]:
    share = await _load_share(session, share_id)
    share.plan_json = payload.plan
    share.config_json = payload.config
    share.plan_id = str(payload.plan.get("id") or "")[:128] or None
    await session.commit()
    await session.refresh(share)
    return _record(share)


@router.get("/replies")
async def list_replies_by_plan(planId: str, session: DatabaseSession) -> list[dict[str, Any]]:
    """Giver-side replies across every share of a plan, newest first."""
    wanted = planId.strip()[:128]
    if not wanted:
        return []
    share_ids = (
        await session.execute(select(Share.id).where(Share.plan_id == wanted, Share.deleted_at.is_(None)))
    ).scalars().all()
    if not share_ids:
        return []
    rows = (
        await session.execute(
            select(ShareReply)
            .where(ShareReply.share_id.in_(share_ids))
            .order_by(ShareReply.created_at.desc())
        )
    ).scalars().all()
    return [_reply_record(reply) for reply in rows]


@router.get("/{share_id}")
async def fetch_share(share_id: str, session: DatabaseSession) -> dict[str, Any]:
    share = await _load_share(session, share_id)
    record = _record(share)
    record["plan"] = _recipient_plan(share.plan_json)
    return record


@router.get("/{share_id}/replies")
async def list_replies(share_id: str, session: DatabaseSession) -> list[dict[str, Any]]:
    await _load_share(session, share_id)
    rows = (
        await session.execute(
            select(ShareReply)
            .where(ShareReply.share_id == share_id)
            .order_by(ShareReply.created_at.asc())
        )
    ).scalars().all()
    return [_reply_record(reply) for reply in rows]


@router.post("/{share_id}/replies", status_code=status.HTTP_201_CREATED)
async def send_reply(
    share_id: str, payload: ShareReplyRequest, session: DatabaseSession
) -> dict[str, Any]:
    await _load_share(session, share_id)
    reply = ShareReply(share_id=share_id, content=payload.content, reaction=payload.reaction)
    session.add(reply)
    await session.commit()
    await session.refresh(reply)
    return _reply_record(reply)


def _reply_record(reply: ShareReply) -> dict[str, Any]:
    return {
        "id": reply.id,
        "shareId": reply.share_id,
        "content": reply.content,
        "reaction": reply.reaction,
        "createdAt": reply.created_at.isoformat(),
    }
