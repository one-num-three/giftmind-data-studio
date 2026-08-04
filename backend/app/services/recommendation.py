"""Deterministic hard filtering and stable candidate scoring."""

import re

from backend.app.schemas.planning import (
    CatalogCandidate,
    PlanningAnswers,
    PlanningProfile,
    RecommendationResult,
)

RECIPIENT_MAP = {
    "女朋友 / 妻子": ["partner_female", "partner"], "男朋友 / 丈夫": ["partner_male", "partner"],
    "父母": ["parent"], "闺蜜 / 好友": ["friend"], "同事 / 上司": ["colleague", "manager"],
    "孩子 / 晚辈": ["child", "junior"],
}
OCCASION_MAP = {"生日": ["birthday"], "纪念日": ["anniversary"], "节日": ["festival"], "毕业 / 里程碑": ["milestone"], "道歉 / 和好": ["apology"], "没有理由，就想送": ["just_because"]}
TIMING_DAYS = {"就今明两天": 2, "一周内": 7, "两到四周": 28, "一个月以上": 60}


def normalize_answers(answers: PlanningAnswers) -> PlanningProfile:
    budget_min, budget_max = _budget(answers.budget)
    kinds = []
    for style in answers.style:
        if "体验" in style or "活动" in style or "旅行" in style:
            kinds.append("activity")
        if any(word in style for word in ("实物", "定制", "数字", "组合")):
            kinds.append("product")
    memory_words = [word for word in re.split(r"[\s，。！？、；：,.!?]+", answers.memory or "") if len(word) >= 2][:12]
    return PlanningProfile(
        recipient_codes=RECIPIENT_MAP.get(answers.recipient or "", [answers.recipient] if answers.recipient else []),
        occasion_codes=OCCASION_MAP.get(answers.occasion or "", [answers.occasion] if answers.occasion else []),
        budget_min=budget_min,
        budget_max=budget_max,
        available_days=TIMING_DAYS.get(answers.timing or ""),
        trait_codes=answers.personality,
        taboo_codes=answers.taboo,
        desired_feeling_codes=[answers.feeling] if answers.feeling else [],
        preferred_kinds=list(dict.fromkeys(kinds)),
        memory_text=answers.memory or "",
        memory_keywords=memory_words,
        city=answers.city,
    )


def rank_candidates(
    profile: PlanningProfile,
    catalog: list[CatalogCandidate],
    *,
    exclude_ids: tuple[str, ...] | list[str] = (),
) -> RecommendationResult:
    excluded: dict[str, str] = {}
    ranked: list[CatalogCandidate] = []
    denied = set(exclude_ids)
    for candidate in catalog:
        reason = _hard_exclusion(profile, candidate, denied)
        if reason:
            excluded[candidate.catalog_id] = reason
            continue
        score, matched = _score(profile, candidate)
        ranked.append(candidate.model_copy(update={"score": score, "matched": matched}))
    ranked.sort(key=lambda item: (-item.score, item.catalog_id))
    return RecommendationResult(ranked=ranked, excluded=excluded)


def _hard_exclusion(profile: PlanningProfile, item: CatalogCandidate, denied: set[str]) -> str | None:
    if item.catalog_id in denied:
        return "excluded_by_request"
    if profile.preferred_kinds and item.kind not in profile.preferred_kinds:
        return "wrong_kind"
    if profile.budget_max is not None and item.price_max > profile.budget_max:
        return "over_budget"
    if profile.available_days is not None and item.lead_days_max > profile.available_days and not (item.rush_available and item.lead_days_min <= profile.available_days):
        return "not_enough_time"
    if _overlap(profile.taboo_codes, item.taboo_flags):
        return "taboo"
    if _overlap(profile.recipient_codes, item.unsuitable_groups):
        return "unsuitable_recipient"
    if item.kind == "activity" and item.activity_mode not in (None, "online"):
        if not profile.city:
            return "city_required"
        if item.service_regions and profile.city not in item.service_regions:
            return "wrong_city"
    return None


def _score(profile: PlanningProfile, item: CatalogCandidate) -> tuple[float, list[str]]:
    score = item.completeness_score * 0.05
    matched: list[str] = []
    dimensions = (
        (profile.memory_keywords, [*item.memory_hooks, *item.tags], 30, "memory"),
        (profile.trait_codes, item.traits, 20, "traits"),
        (profile.occasion_codes, item.occasions, 15, "occasion"),
        (profile.desired_feeling_codes, item.desired_feelings, 10, "feeling"),
        (profile.recipient_codes, item.recipient_types, 10, "recipient"),
    )
    for wanted, offered, weight, label in dimensions:
        ratio = _ratio(wanted, offered)
        if ratio:
            score += weight * ratio
            matched.append(label)
    if profile.budget_max is not None and item.price_max <= profile.budget_max:
        score += 5
        matched.append("budget")
    if profile.available_days is not None and item.lead_days_max <= profile.available_days:
        score += 5
        matched.append("timing")
    return round(min(100, score), 2), matched


def _budget(value: str | dict | None) -> tuple[float, float | None]:
    if isinstance(value, dict):
        low = float(value.get("min") or 0)
        high = value.get("max")
        return low, float(high) if high is not None else None
    numbers = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", str(value or ""))]
    return (numbers[0], numbers[-1]) if len(numbers) >= 2 else (0, numbers[0] if numbers else None)


def _norm(values: list[str]) -> set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip() and value != "*"}


def _overlap(left: list[str], right: list[str]) -> bool:
    return bool(_norm(left) & _norm(right))


def _ratio(wanted: list[str], offered: list[str]) -> float:
    target = _norm(wanted)
    if not target:
        return 0
    available = _norm(offered)
    if "*" in {str(value).strip() for value in offered}:
        return 0.5
    return len(target & available) / len(target)
