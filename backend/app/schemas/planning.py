"""Versioned contracts for the local GiftMind H5 planning API."""

from typing import Any

from pydantic import Field

from backend.app.schemas.common import APIModel


class PlanningAnswers(APIModel):
    recipient: str | None = None
    occasion: str | None = None
    timing: str | None = None
    budget: str | dict[str, Any] | None = None
    personality: list[str] = Field(default_factory=list)
    taboo: list[str] = Field(default_factory=list)
    memory: str | None = None
    relationship_note: str | None = None
    feeling: str | None = None
    style: list[str] = Field(default_factory=list)
    city: str | None = None


class GeneratePlanRequest(APIModel):
    request_id: str = Field(min_length=1, max_length=128)
    answers: PlanningAnswers


class ReplaceGiftRequest(APIModel):
    request_id: str
    answers: PlanningAnswers
    current_catalog_ids: list[str] = Field(default_factory=list)
    replace_catalog_id: str
    reason: str = "other"
    reason_note: str = ""
    locked_catalog_ids: list[str] = Field(default_factory=list)
    current_plan: dict[str, Any] | None = None


class RewriteLetterRequest(APIModel):
    request_id: str
    answers: PlanningAnswers
    gifts: list[dict[str, Any]] = Field(default_factory=list)
    current_letter: dict[str, Any] | None = None
    tone: str = "warm"
    instruction: str = ""


class RewriteRitualRequest(APIModel):
    request_id: str
    answers: PlanningAnswers
    gifts: list[dict[str, Any]] = Field(default_factory=list)
    current_ritual: list[dict[str, Any]] = Field(default_factory=list)
    instruction: str = ""


class ChatRequest(APIModel):
    request_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    answers: PlanningAnswers
    plan: dict[str, Any] | None = None


class PlanningProfile(APIModel):
    recipient_codes: list[str] = Field(default_factory=list)
    occasion_codes: list[str] = Field(default_factory=list)
    budget_min: float = Field(default=0, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    available_days: int | None = Field(default=None, ge=0)
    trait_codes: list[str] = Field(default_factory=list)
    taboo_codes: list[str] = Field(default_factory=list)
    desired_feeling_codes: list[str] = Field(default_factory=list)
    preferred_kinds: list[str] = Field(default_factory=list)
    memory_text: str = ""
    memory_keywords: list[str] = Field(default_factory=list)
    city: str | None = None


class CatalogCandidate(APIModel):
    catalog_id: str
    name: str
    kind: str
    category: str
    description: str | None = None
    emoji: str = "🎁"
    price_min: float = 0
    price_max: float = 0
    currency: str = "CNY"
    recipient_types: list[str] = Field(default_factory=list)
    relationship_stages: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)
    desired_feelings: list[str] = Field(default_factory=list)
    memory_hooks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    taboo_flags: list[str] = Field(default_factory=list)
    unsuitable_groups: list[str] = Field(default_factory=list)
    lead_days_min: int = 0
    lead_days_max: int = 0
    rush_available: bool = False
    why_template: str | None = None
    tip: str | None = None
    activity_mode: str | None = None
    service_regions: list[str] = Field(default_factory=list)
    completeness_score: int = 0
    score: float = 0
    matched: list[str] = Field(default_factory=list)


class RecommendationResult(APIModel):
    ranked: list[CatalogCandidate] = Field(default_factory=list)
    excluded: dict[str, str] = Field(default_factory=dict)
