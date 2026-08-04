"""Pydantic output contracts shared by versioned prompts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

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
