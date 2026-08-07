"""Deterministic four-block summary for the H5 confirmation page."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.app.schemas.planning import PlanningAnswers


def compose_summary(answers: PlanningAnswers) -> dict[str, dict[str, Any]]:
    """Return the four editable confirmation blocks derived from answers."""
    recipient = _text(answers.recipient, "对方")
    occasion = _text(answers.occasion, "一个特别的日子")
    timing = _text(answers.timing)

    who = f"送给{recipient}，为{occasion}"
    if timing:
        who += f"，计划{timing}内送出"

    story = _text(answers.memory) or _text(answers.relationship_note)
    story = story or "还没有提到具体的回忆，可以在下一步补充一句。"

    feeling = _text(answers.feeling) or "希望 TA 感到被认真对待"

    constraints = _constraints_text(answers)
    return {
        "who": {"label": "TA 是谁", "text": who, "fields": ["recipient"]},
        "story": {"label": "你们的故事", "text": story, "fields": ["memory"]},
        "feeling": {"label": "这次想表达什么", "text": feeling, "fields": ["feeling"]},
        "constraints": {
            "label": "预算与约束",
            "text": constraints,
            "fields": ["budget", "timing", "taboo", "style", "city", "summaryNotes"],
        },
    }


def _constraints_text(answers: PlanningAnswers) -> str:
    parts: list[str] = []
    if answers.budget is not None:
        parts.append(f"预算：{_budget_text(answers.budget)}")
    if answers.timing:
        parts.append(f"时间：{answers.timing}")
    if answers.taboo:
        parts.append(f"避开：{'、'.join(answers.taboo)}")
    if answers.style:
        parts.append(f"形式偏好：{'、'.join(answers.style)}")
    if answers.city:
        parts.append(f"所在城市：{answers.city}")
    if answers.summary_notes:
        parts.append(f"补充说明：{answers.summary_notes}")
    return "；".join(parts) if parts else "暂无特殊约束"


def _budget_text(value: str | Mapping[str, Any]) -> str:
    if isinstance(value, Mapping):
        low = value.get("min")
        high = value.get("max")
        if low is not None and high is not None:
            return f"¥{low}–{high}"
        if low is not None:
            return f"¥{low} 起"
        if high is not None:
            return f"不超过 ¥{high}"
    return str(value or "")


def _text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback
