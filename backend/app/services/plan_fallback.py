"""Deterministic plan composition used when DeepSeek is unavailable or invalid."""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any


def compose_rule_plan(
    answers: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
) -> dict[str, Any]:
    """Build an H5-compatible plan without inventing catalog facts."""
    selected = list(candidates[:3])
    if not selected:
        raise ValueError("at least one eligible catalog candidate is required")

    recipient = _text(answers.get("recipient"), "对方")
    occasion = _text(answers.get("occasion"), "这次特别的时刻")
    memory = _text(answers.get("memory"))
    feeling = _text(answers.get("feeling"), "被认真理解")
    memory_line = f"你提到的“{memory[:36]}”是这份方案最重要的线索。" if memory else "这份方案优先照顾对方真实的日常与感受。"

    gifts = [gift_snapshot(candidate, rank=index + 1) for index, candidate in enumerate(selected)]
    first_name = gifts[0]["name"]
    return {
        "schemaVersion": "giftmind.plan.v1",
        "source": "rule_fallback",
        "model": None,
        "promptVersion": "rule_fallback_v1",
        "requestId": request_id,
        "profile": {"recipient": recipient, "occasion": occasion, "feeling": feeling},
        "title": f"给{recipient}的一份心意",
        "subtitle": f"围绕{occasion}，从真实礼物库里挑出的可执行方案",
        "insight": {
            "summary": f"{memory_line} 与其追求昂贵或夸张，更适合让礼物回应“{feeling}”。",
            "traits": [value for value in _list(answers.get("personality"))[:2]] + ["认真准备"],
            "keyPoint": "目录事实和用户边界优先，文案保持克制。",
        },
        "gifts": gifts,
        "letter": {
            "salutation": f"给{recipient}：",
            "paragraphs": [
                f"想在{occasion}把这份心意认真地交给你。",
                memory_line,
                f"最后选了{first_name}，不是因为它最夸张，而是希望你能感到{feeling}。",
            ],
            "signature": "—— 想认真表达心意的我",
            "tone": "克制真诚",
        },
        "ritual": [
            {"time": "提前准备", "title": "确认细节", "desc": gifts[0]["tip"] or "确认时间、规格与交付方式。"},
            {"time": "送出当天", "title": "留一点安静", "desc": "不要急着解释，让对方先看到礼物和信。"},
            {"time": "递出时", "title": "说一句真实的话", "desc": f"告诉对方：我希望你在{occasion}感到{feeling}。"},
        ],
        "share": {"greeting": "有一份为你认真准备的心意", "coverEmoji": gifts[0]["emoji"], "theme": "warm"},
        "debug": None,
    }


def gift_snapshot(candidate: Mapping[str, Any], *, rank: int, why: str | None = None) -> dict[str, Any]:
    catalog_id = _text(candidate.get("catalogId") or candidate.get("id"))
    name = _text(candidate.get("name") or candidate.get("canonicalName"), "未命名礼物")
    kind = _text(candidate.get("kind") or candidate.get("giftTypeCode"), "product")
    category = _text(candidate.get("category"), "体验" if kind == "activity" else "实物")
    low = _number(candidate.get("priceMin") or candidate.get("price_min"))
    high = _number(candidate.get("priceMax") or candidate.get("price_max"), low)
    score = int(max(0, min(100, _number(candidate.get("score"), 80 - (rank - 1) * 4))))
    return {
        "id": catalog_id,
        "catalogId": catalog_id,
        "emoji": _text(candidate.get("emoji"), "🎁"),
        "name": name,
        "why": _text(why or candidate.get("why") or candidate.get("whyTemplate"), "它与当前对象、场合和预算的匹配度较高，且准备条件可执行。"),
        "price": _price(low, high),
        "category": category,
        "tags": _list(candidate.get("tags"))[:3],
        "matchScore": score,
        "tip": _text(candidate.get("tip") or candidate.get("purchaseOrBookingTip")),
        "leadTime": _lead_time(candidate),
        "kind": kind,
    }


def _lead_time(candidate: Mapping[str, Any]) -> str:
    days = int(_number(candidate.get("leadDays") or candidate.get("leadDaysMax")))
    if days <= 0:
        return "通常可当天准备"
    return f"建议提前 {days} 天确认"


def _price(low: float, high: float) -> str:
    if low == high:
        return f"¥{_compact(low)}"
    return f"¥{_compact(low)}–{_compact(high)}"


def _compact(value: float) -> str:
    decimal = Decimal(str(value))
    return format(decimal.quantize(Decimal(1)) if decimal == decimal.to_integral() else decimal.normalize(), "f")


def _number(value: Any, fallback: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [text for item in value if (text := _text(item))]
    text = _text(value)
    return [text] if text else []
