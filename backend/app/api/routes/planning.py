"""Local-only planning endpoints consumed by the GiftMind H5 prototype."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db_session
from backend.app.models.gift import Gift
from backend.app.prompts import (
    gift_replace,
    letter_rewrite,
    plan_compose,
    ritual_rewrite,
)
from backend.app.prompts.schemas import (
    GiftReplaceOutput,
    LetterRewriteOutput,
    PlanComposeOutput,
    RitualRewriteOutput,
)
from backend.app.schemas.planning import (
    ChatRequest,
    GeneratePlanRequest,
    ReplaceGiftRequest,
    RewriteLetterRequest,
    RewriteRitualRequest,
    SummaryRequest,
)
from backend.app.services.catalog_query import load_active_catalog
from backend.app.services.deepseek_client import DeepSeekClient, DeepSeekError
from backend.app.services.plan_ai_mapper import InvalidAIPlanError, compose_ai_plan
from backend.app.services.plan_fallback import compose_rule_plan, gift_snapshot
from backend.app.services.plan_summary import compose_summary
from backend.app.services.recommendation import normalize_answers, rank_candidates

router = APIRouter(prefix="/api/h5", tags=["h5-planning"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/status")
async def get_planning_status(
    request: Request,
    session: DatabaseSession,
) -> dict[str, object]:
    """Return a non-secret readiness snapshot for the local H5."""
    active_count = await session.scalar(
        select(func.count(Gift.id)).where(
            Gift.status == "active",
            Gift.deleted_at.is_(None),
            Gift.completeness_score >= 60,
        )
    )
    settings = request.app.state.settings
    model = getattr(settings, "deepseek_model", "deepseek-v4-flash")
    configured = bool(getattr(settings, "deepseek_api_key", None))
    return {
        "ok": True,
        "deepseekConfigured": configured,
        "model": model,
        "activeGiftCount": int(active_count or 0),
        "mode": "deepseek" if configured else "rules",
        "voiceConfigured": bool(
            getattr(settings, "voice_asr_provider", "").strip()
            and getattr(settings, "voice_asr_base_url", "").strip()
            and getattr(settings, "voice_asr_api_key", None)
        ),
        "promptVersions": {
            "profileExtract": "profile_extract_v1",
            "planCompose": "plan_compose_v1",
        },
    }


@router.post("/plans/summary")
async def summarize_answers(payload: SummaryRequest) -> dict[str, object]:
    """Derive the editable four-block summary before plan generation."""
    return {
        "requestId": payload.request_id,
        "source": "rule",
        "summary": compose_summary(payload.answers),
    }


@router.post("/plans/generate")
async def generate_plan(
    payload: GeneratePlanRequest,
    request: Request,
    session: DatabaseSession,
) -> dict[str, object]:
    profile = normalize_answers(payload.answers)
    recommendation = rank_candidates(profile, await load_active_catalog(session))
    if len(recommendation.ranked) < 3:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_CANDIDATES", "message": "没有至少三件同时满足硬约束的礼物"},
        )
    # Ranking and hard constraints are deterministic. Giving the model the best
    # ten candidates is enough to choose three while keeping the prompt small
    # enough for the flash model to respond reliably.
    candidate_models = recommendation.ranked[:10]
    candidates = [item.model_dump(by_alias=True) for item in candidate_models]
    client = DeepSeekClient(request.app.state.settings)
    if client.configured:
        try:
            result = await client.complete_json(
                operation="plan_compose",
                prompt_version=plan_compose.PROMPT_VERSION,
                system_prompt=plan_compose.SYSTEM_PROMPT,
                user_payload=plan_compose.user_payload(profile.model_dump(by_alias=True), candidates),
                output_model=PlanComposeOutput,
                schema_hint=plan_compose.SCHEMA_HINT,
                session=session,
            )
            return compose_ai_plan(
                payload.answers.model_dump(by_alias=True),
                candidates,
                result.data,
                request_id=payload.request_id,
                model=result.model,
                prompt_version=result.prompt_version,
            )
        except (DeepSeekError, InvalidAIPlanError):
            pass
    return compose_rule_plan(
        payload.answers.model_dump(by_alias=True),
        candidates[:3],
        request_id=payload.request_id,
    )


@router.post("/plans/gifts/replace")
async def replace_gift(
    payload: ReplaceGiftRequest,
    request: Request,
    session: DatabaseSession,
) -> dict[str, object]:
    profile = normalize_answers(payload.answers)
    excluded = [*payload.current_catalog_ids, *payload.locked_catalog_ids, payload.replace_catalog_id]
    ranked = rank_candidates(profile, await load_active_catalog(session), exclude_ids=excluded).ranked
    if not ranked:
        raise HTTPException(status_code=409, detail={"code": "NO_CANDIDATES", "message": "没有合适的替代礼物"})
    candidates = [item.model_dump(by_alias=True) for item in ranked[:12]]
    chosen = candidates[0]
    why: str | None = None
    client = DeepSeekClient(request.app.state.settings)
    if client.configured:
        try:
            result = await client.complete_json(
                operation="gift_replace",
                prompt_version=gift_replace.PROMPT_VERSION,
                system_prompt=gift_replace.SYSTEM_PROMPT,
                user_payload=gift_replace.user_payload(
                    profile.model_dump(by_alias=True), candidates, payload.replace_catalog_id,
                    payload.locked_catalog_ids, f"{payload.reason}: {payload.reason_note}".strip(),
                ),
                output_model=GiftReplaceOutput,
                schema_hint=gift_replace.SCHEMA_HINT,
                session=session,
            )
            by_id = {item["catalogId"]: item for item in candidates}
            if result.data.catalog_id in by_id:
                chosen = by_id[result.data.catalog_id]
                why = result.data.why
        except DeepSeekError:
            pass
    return {"gift": gift_snapshot(chosen, rank=1, why=why)}


@router.post("/plans/letter/rewrite")
async def rewrite_letter(
    payload: RewriteLetterRequest,
    request: Request,
    session: DatabaseSession,
) -> dict[str, object]:
    client = DeepSeekClient(request.app.state.settings)
    if client.configured:
        try:
            result = await client.complete_json(
                operation="letter_rewrite",
                prompt_version=letter_rewrite.PROMPT_VERSION,
                system_prompt=letter_rewrite.SYSTEM_PROMPT,
                user_payload=letter_rewrite.user_payload(
                    payload.answers.model_dump(by_alias=True), payload.gifts,
                    payload.current_letter or {}, payload.tone, payload.instruction,
                ),
                output_model=LetterRewriteOutput,
                schema_hint=letter_rewrite.SCHEMA_HINT,
                session=session,
            )
            body = result.data.letter.body
            return {"letter": {"salutation": result.data.letter.salutation, "paragraphs": [line.strip() for line in body.split("\n") if line.strip()], "signature": result.data.letter.closing, "tone": result.data.tone}}
        except DeepSeekError:
            pass
    current = dict(payload.current_letter or {})
    current["tone"] = payload.tone
    if payload.instruction:
        paragraphs = list(current.get("paragraphs") or [])
        paragraphs.append(payload.instruction)
        current["paragraphs"] = paragraphs
    return {"letter": current}


@router.post("/plans/ritual/rewrite")
async def rewrite_ritual(
    payload: RewriteRitualRequest,
    request: Request,
    session: DatabaseSession,
) -> dict[str, object]:
    client = DeepSeekClient(request.app.state.settings)
    if client.configured:
        try:
            result = await client.complete_json(
                operation="ritual_rewrite",
                prompt_version=ritual_rewrite.PROMPT_VERSION,
                system_prompt=ritual_rewrite.SYSTEM_PROMPT,
                user_payload=ritual_rewrite.user_payload(
                    payload.answers.model_dump(by_alias=True), payload.gifts,
                    payload.answers.timing or "", payload.answers.occasion or "", payload.instruction,
                ),
                output_model=RitualRewriteOutput,
                schema_hint=ritual_rewrite.SCHEMA_HINT,
                session=session,
            )
            return {"ritual": [{"time": step.timing or "", "title": step.title, "desc": step.description} for step in result.data.ritual]}
        except DeepSeekError:
            pass
    ritual = list(payload.current_ritual)
    if payload.instruction and ritual:
        ritual[-1] = {**ritual[-1], "desc": payload.instruction}
    return {"ritual": ritual}


@router.post("/chat")
async def chat(payload: ChatRequest) -> dict[str, str]:
    last = str(payload.messages[-1].get("content") or "") if payload.messages else ""
    reply = "我已经记下这条修改意见。请使用礼物替换、信件或仪式按钮把它应用到对应部分。"
    if last:
        reply = f"我记下了“{last[:60]}”。请选择要修改的礼物、信件或仪式，我只改那一部分。"
    return {"reply": reply}
