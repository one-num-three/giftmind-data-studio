"""Validate model selections and merge prose with immutable catalog facts."""

from collections.abc import Mapping, Sequence
from typing import Any

from backend.app.prompts.schemas import PlanComposeOutput
from backend.app.services.plan_fallback import gift_snapshot


class InvalidAIPlanError(ValueError):
    """The model output cannot be safely projected onto the approved catalog."""


def compose_ai_plan(
    answers: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    output: PlanComposeOutput,
    *,
    request_id: str,
    model: str,
    prompt_version: str,
) -> dict[str, Any]:
    catalog = {_catalog_id(item): item for item in candidates}
    selected_ids = [item.catalog_id for item in output.selected]
    if len(selected_ids) != 3 or len(set(selected_ids)) != 3:
        raise InvalidAIPlanError("model must select three distinct catalog IDs")
    unknown = [catalog_id for catalog_id in selected_ids if catalog_id not in catalog]
    if unknown:
        raise InvalidAIPlanError(f"model selected IDs outside the candidate whitelist: {unknown}")

    ordered = sorted(output.selected, key=lambda item: item.rank)
    gifts = [
        gift_snapshot(catalog[item.catalog_id], rank=index + 1, why=item.why)
        for index, item in enumerate(ordered)
    ]
    memory = str(answers.get("memory") or "").strip()
    traits = [str(value) for value in answers.get("personality") or [] if str(value).strip()]
    paragraphs = [part.strip() for part in output.letter.body.split("\n") if part.strip()]
    if not paragraphs:
        paragraphs = [output.letter.body.strip()]

    return {
        "schemaVersion": "giftmind.plan.v1",
        "source": "deepseek",
        "model": model,
        "promptVersion": prompt_version,
        "requestId": request_id,
        "profile": {
            "recipient": answers.get("recipient"),
            "occasion": answers.get("occasion"),
            "memory": memory,
        },
        "title": output.title,
        "subtitle": output.subtitle,
        "insight": {
            "summary": output.relationship_insight,
            "traits": traits[:3] or ["认真准备"],
            "keyPoint": "礼物事实来自当前已启用目录。",
        },
        "gifts": gifts,
        "letter": {
            "salutation": output.letter.salutation,
            "paragraphs": paragraphs,
            "signature": output.letter.closing,
            "tone": "自然",
        },
        "ritual": [
            {"time": step.timing or "", "title": step.title, "desc": step.description}
            for step in output.ritual
        ],
        "share": {"greeting": "有一份为你认真准备的心意", "coverEmoji": gifts[0]["emoji"], "theme": "warm"},
        "debug": None,
    }


def _catalog_id(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("catalogId") or candidate.get("id") or "").strip()
