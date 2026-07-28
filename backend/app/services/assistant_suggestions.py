"""Normalize assistant output into a strict, reviewable field patch."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re

import httpx


FIELD_DEFINITIONS: dict[str, tuple[str, str]] = {
    "canonicalName": ("标准名称", "text"),
    "giftTypeCode": ("礼物类型", "type"),
    "shortDescription": ("简短说明", "text"),
    "priceMin": ("最低价格", "number"),
    "priceMax": ("最高价格", "number"),
    "isFree": ("免费", "boolean"),
    "whyTemplate": ("送礼理由", "text"),
    "recipientTypes": ("适合对象", "list"),
    "occasions": ("适合场景", "list"),
    "interests": ("兴趣标签", "list"),
    "tags": ("检索标签", "list"),
    "productDetails.genericProductName": ("通用商品名", "text"),
    "productDetails.materials": ("材质", "list"),
    "productDetails.personalizationMethods": ("定制方式", "list"),
    "productDetails.shippingRequired": ("需要配送", "boolean"),
    "activityDetails.activityCategory": ("活动类别", "text"),
    "activityDetails.serviceRegions": ("服务区域", "list"),
    "activityDetails.durationMinutesMin": ("最短时长", "number"),
    "activityDetails.durationMinutesMax": ("最长时长", "number"),
    "activityDetails.participantsMin": ("最少人数", "number"),
    "activityDetails.participantsMax": ("最多人数", "number"),
    "activityDetails.bookingRequired": ("需要预约", "boolean"),
    "activityDetails.bookingLeadDaysMin": ("最少提前预约天数", "number"),
    "activityDetails.bookingLeadDaysMax": ("最多提前预约天数", "number"),
}


def _clamp_confidence(value: object, fallback: float = 0.35) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return round(max(0.0, min(1.0, number)), 2)


def _normalize_value(kind: str, value: object) -> object | None:
    if kind == "type":
        return value if value in {"product", "activity"} else None
    if kind == "text":
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    if kind == "number":
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number < 0:
            return None
        return int(number) if number.is_integer() else round(number, 2)
    if kind == "boolean":
        return value if isinstance(value, bool) else None
    if kind == "list":
        if not isinstance(value, list):
            return None
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items or None
    return None


def _flatten(raw: Mapping[str, object]) -> dict[str, object]:
    flattened: dict[str, object] = {}
    recommended_type = raw.get("recommendedGiftTypeCode")
    if recommended_type is not None:
        flattened["giftTypeCode"] = recommended_type
    for path in FIELD_DEFINITIONS:
        if path == "giftTypeCode":
            continue
        if "." not in path:
            if path in raw:
                flattened[path] = raw[path]
            continue
        section, field = path.split(".", 1)
        nested = raw.get(section)
        if isinstance(nested, Mapping) and field in nested:
            flattened[path] = nested[field]
    return flattened


def _source_labels(source_refs: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for source in source_refs:
        label = str(source.get("label") or source.get("url") or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels or ["用户描述"]


def suggestion_to_patches(
    raw: Mapping[str, object],
    source_refs: list[dict[str, object]],
) -> list[dict[str, object]]:
    overall = _clamp_confidence(raw.get("confidence"))
    field_confidence = raw.get("fieldConfidence")
    confidence_map = field_confidence if isinstance(field_confidence, Mapping) else {}
    sources = _source_labels(source_refs)
    patches: list[dict[str, object]] = []
    for path, value in _flatten(raw).items():
        label, kind = FIELD_DEFINITIONS[path]
        normalized = _normalize_value(kind, value)
        if normalized is None:
            continue
        confidence = _clamp_confidence(confidence_map.get(path), overall)
        patches.append(
            {
                "path": path,
                "label": label,
                "value": deepcopy(normalized),
                "confidence": confidence,
                "sourceRefs": sources.copy(),
                "status": "pending",
            }
        )
    return patches


def _fallback_raw(
    content: str,
    gift_type_code: str,
    source_refs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    clean = re.sub(r"https?://\S+", "", content).strip()
    first_source = next((item for item in source_refs or [] if item.get("status") == "ok"), {})
    source_title = str(first_source.get("title") or first_source.get("label") or "").strip()
    source_description = str(first_source.get("description") or first_source.get("text") or "").strip()
    display_name = clean[:80] or source_title[:80]
    number_pattern = r"\d+(?:\.\d{1,2})?"
    price_range = re.search(
        rf"(?:¥|￥|约|预算|价格|价)?\s*({number_pattern})\s*(?:到|至|[-~～])\s*({number_pattern})\s*元",
        content,
    )
    price_match = re.search(rf"(?:¥|￥|约|价格|价)?\s*({number_pattern})\s*元", content)
    if price_range:
        first_price, second_price = (float(price_range.group(1)), float(price_range.group(2)))
        price_min, price_max = sorted((first_price, second_price))
    else:
        if price_match is None:
            price_match = re.search(
                rf"({number_pattern})",
                " ".join(map(str, first_source.get("priceHints") or [])),
            )
        price_min = price_max = float(price_match.group(1)) if price_match else None
    raw: dict[str, object] = {
        "canonicalName": display_name or None,
        "recommendedGiftTypeCode": gift_type_code,
        "shortDescription": (source_description[:120] or clean[:120]) or "请结合来源补充礼物说明。",
        "whyTemplate": f"可以把{display_name[:40] or '这份礼物'}送给合适的对象，请人工确认具体匹配关系。",
        "priceMin": price_min,
        "priceMax": price_max,
        "confidence": 0.42,
    }
    if gift_type_code == "product":
        materials = [name for name in ("黄铜", "金属", "木质", "陶瓷", "玻璃", "皮革") if name in content]
        raw["productDetails"] = {"materials": materials}
    else:
        raw["activityDetails"] = {}
    return raw


def _assistant_prompt(gift_type_code: str) -> str:
    return f"""You help a Chinese gift-data collection team. Return one JSON object only.
The currently selected type is {gift_type_code}. Use supplied conversation, source extracts,
and current form values. Never invent a merchant, exact URL, address, or unsupported fact.
Return canonicalName, recommendedGiftTypeCode, shortDescription, priceMin, priceMax, isFree, whyTemplate,
recipientTypes[], occasions[], interests[], tags[], confidence, fieldConfidence,
followUpQuestions[] with at most 3 concise questions for important facts that remain unknown, plus
productDetails {{genericProductName, materials[], personalizationMethods[], shippingRequired}}
or activityDetails {{activityCategory, serviceRegions[], durationMinutesMin,
durationMinutesMax, participantsMin, participantsMax, bookingRequired,
bookingLeadDaysMin, bookingLeadDaysMax}}. Use null or [] when unknown."""


def _missing_information_questions(
    current_values: Mapping[str, object],
    gift_type_code: str,
) -> list[str]:
    candidates: list[str] = []
    if not current_values.get("canonicalName"):
        candidates.append("这份礼物的标准名称是什么？")
    if current_values.get("priceMin") is None and current_values.get("priceMax") is None:
        candidates.append("它通常的价格区间是多少？如果免费也请说明。")
    if not current_values.get("recipientTypes"):
        candidates.append("它最适合送给哪些对象？")
    if not current_values.get("occasions"):
        candidates.append("它最适合生日、纪念日、感谢还是其他场景？")
    details = current_values.get(f"{gift_type_code}Details")
    nested = details if isinstance(details, Mapping) else {}
    if gift_type_code == "product":
        if not nested.get("materials"):
            candidates.append("商品的主要材质是什么？")
        if nested.get("shippingRequired") is None:
            candidates.append("这是数字商品，还是需要实体配送？")
    else:
        if nested.get("durationMinutesMin") is None:
            candidates.append("活动大约持续多长时间？")
        if nested.get("participantsMin") is None:
            candidates.append("活动适合几个人参加？")
        if not nested.get("serviceRegions"):
            candidates.append("活动可在哪些城市或线上提供？")
    return candidates[:3]


def _parse_json_object(content: str) -> dict[str, object]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("missing JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("assistant result is not an object")
    return value


async def generate_assistant_result(
    *,
    content: str,
    gift_type_code: str,
    current_values: dict[str, object],
    history: list[dict[str, str]],
    source_refs: list[dict[str, object]],
    api_key: str | None,
) -> dict[str, object]:
    raw = _fallback_raw(content, gift_type_code, source_refs)
    source = "rule"
    if api_key:
        context_sources = [
            {
                "url": item.get("url"),
                "status": item.get("status"),
                "title": item.get("title"),
                "description": item.get("description"),
                "text": str(item.get("text") or "")[:6000],
                "structuredData": item.get("structuredData") or [],
                "priceHints": item.get("priceHints") or [],
            }
            for item in source_refs
        ]
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                latest_payload = json.dumps(
                    {
                        "conversation": history[-12:],
                        "latestMessage": content,
                        "sources": context_sources,
                        "currentValues": current_values,
                    },
                    ensure_ascii=False,
                )
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "deepseek-v4-flash",
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": _assistant_prompt(gift_type_code)},
                            {
                                "role": "user",
                                "content": latest_payload,
                            },
                        ],
                    },
                )
                response.raise_for_status()
                raw = _parse_json_object(response.json()["choices"][0]["message"]["content"])
                source = "deepseek"
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            source = "rule"
    patches = suggestion_to_patches(raw, source_refs)
    model_questions = raw.get("followUpQuestions")
    questions = (
        [str(question).strip() for question in model_questions if str(question).strip()][:3]
        if isinstance(model_questions, list)
        else []
    )
    for question in _missing_information_questions(current_values, gift_type_code):
        if len(questions) >= 3:
            break
        if question not in questions:
            questions.append(question)
    confidence = (
        round(sum(float(item["confidence"]) for item in patches) / len(patches), 2)
        if patches
        else 0.0
    )
    question_text = "\n还需要确认：\n" + "\n".join(f"• {question}" for question in questions) if questions else ""
    return {
        "content": f"已整理出 {len(patches)} 条字段建议。请逐项审核后再写入表单。{question_text}",
        "patches": patches,
        "confidence": confidence,
        "source": source,
        "questions": questions,
    }
