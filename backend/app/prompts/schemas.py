"""Pydantic output contracts shared by versioned prompts."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import APIModel


class ProfileExtractOutput(APIModel):
    memory_keywords: list[str] = Field(default_factory=list, max_length=12)
    interest_codes: list[str] = Field(default_factory=list, max_length=12)
    taboo_codes: list[str] = Field(default_factory=list, max_length=12)
    recipient_notes: list[str] = Field(default_factory=list, max_length=8)


class SelectedGiftOutput(APIModel):
    catalog_id: str
    rank: Annotated[int, Field(ge=1, le=20)]
    why: Annotated[str, Field(min_length=1, max_length=600)]
    story_connection: Annotated[str | None, Field(max_length=300)] = None
    caveats: list[str] = Field(default_factory=list, max_length=8)


class LetterOutput(APIModel):
    salutation: Annotated[str, Field(min_length=1, max_length=80)]
    body: Annotated[str, Field(min_length=1, max_length=1600)]
    closing: Annotated[str, Field(min_length=1, max_length=100)]


class RitualStepOutput(APIModel):
    title: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(min_length=1, max_length=500)]
    timing: Annotated[str | None, Field(max_length=100)] = None


class PlanComposeOutput(APIModel):
    title: Annotated[str, Field(min_length=1, max_length=100)]
    subtitle: Annotated[str, Field(min_length=1, max_length=240)]
    relationship_insight: Annotated[str, Field(min_length=1, max_length=800)]
    selected: Annotated[list[SelectedGiftOutput], Field(min_length=3, max_length=3)]
    letter: LetterOutput
    ritual: Annotated[list[RitualStepOutput], Field(min_length=1, max_length=8)]

    @model_validator(mode="before")
    @classmethod
    def normalize_flash_model_shape(cls, value: Any) -> Any:
        """Normalize predictable v4-flash presentation variants only."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        selected = _decode_json_container(normalized.get("selected"))
        if isinstance(selected, list):
            normalized["selected"] = [
                _normalize_selected_item(item, index)
                for index, item in enumerate(selected, start=1)
            ]
        normalized["letter"] = _normalize_letter(normalized.get("letter"))
        normalized["ritual"] = _normalize_ritual(normalized.get("ritual"))
        return normalized

    @field_validator("selected", mode="before")
    @classmethod
    def decode_selected_json_strings(cls, value: Any) -> Any:
        decoded = _decode_json_container(value)
        if isinstance(decoded, list):
            return [_decode_json_container(item) for item in decoded]
        return decoded

    @field_validator("letter", mode="before")
    @classmethod
    def decode_letter_json_string(cls, value: Any) -> Any:
        return _decode_json_container(value)

    @field_validator("ritual", mode="before")
    @classmethod
    def decode_ritual_json_strings(cls, value: Any) -> Any:
        decoded = _decode_json_container(value)
        if isinstance(decoded, list):
            return [_decode_json_container(item) for item in decoded]
        return decoded


class GiftReplaceOutput(APIModel):
    catalog_id: str
    why: Annotated[str, Field(min_length=1, max_length=600)]
    story_connection: Annotated[str | None, Field(max_length=300)] = None
    caveats: list[str] = Field(default_factory=list, max_length=8)


class LetterRewriteOutput(APIModel):
    tone: Literal["restrained", "warm", "playful", "solemn", "concise"]
    letter: LetterOutput


class RitualRewriteOutput(APIModel):
    ritual: Annotated[list[RitualStepOutput], Field(min_length=1, max_length=8)]


def _decode_json_container(value: Any) -> Any:
    """Decode model-produced JSON strings only when they contain a container."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        decoded = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value
    return decoded if isinstance(decoded, (dict, list)) else value


def _normalize_selected_item(value: Any, rank: int) -> Any:
    item = _decode_json_container(value)
    if not isinstance(item, dict):
        return item
    return {
        "catalogId": item.get("catalogId") or item.get("catalog_id") or item.get("id"),
        "rank": item.get("rank") or rank,
        "why": item.get("why") or item.get("reason") or item.get("recommendationReason"),
        "storyConnection": item.get("storyConnection") or item.get("story_connection"),
        "caveats": item.get("caveats") or [],
    }


def _normalize_letter(value: Any) -> Any:
    decoded = _decode_json_container(value)
    if isinstance(decoded, dict):
        return decoded
    if not isinstance(decoded, str) or not decoded.strip():
        return decoded
    lines = [line.strip() for line in decoded.splitlines() if line.strip()]
    salutation = lines[0] if lines and len(lines[0]) <= 80 else "给你："
    closing = lines[-1] if len(lines) > 1 and len(lines[-1]) <= 100 else "—— 想认真表达心意的我"
    body_lines = lines[1:-1] if len(lines) > 2 else lines
    body = "\n".join(body_lines).strip() or decoded.strip()
    return {"salutation": salutation, "body": body, "closing": closing}


def _normalize_ritual(value: Any) -> Any:
    decoded = _decode_json_container(value)
    if isinstance(decoded, list):
        return [_normalize_ritual_step(item, index) for index, item in enumerate(decoded, start=1)]
    if not isinstance(decoded, dict):
        return decoded
    for key in ("steps", "ritual", "timeline", "items"):
        nested = _decode_json_container(decoded.get(key))
        if isinstance(nested, list):
            return [_normalize_ritual_step(item, index) for index, item in enumerate(nested, start=1)]
    if "title" in decoded or "description" in decoded:
        return [_normalize_ritual_step(decoded, 1)]
    return [
        _normalize_ritual_step({"title": str(key), "description": item}, index)
        for index, (key, item) in enumerate(decoded.items(), start=1)
    ]


def _normalize_ritual_step(value: Any, index: int) -> Any:
    item = _decode_json_container(value)
    if isinstance(item, str):
        return {"title": f"第 {index} 步", "description": item, "timing": None}
    if not isinstance(item, dict):
        return item
    return {
        "title": item.get("title") or item.get("name") or item.get("step") or f"第 {index} 步",
        "description": item.get("description") or item.get("content") or item.get("action") or item.get("detail"),
        "timing": item.get("timing") or item.get("time"),
    }
