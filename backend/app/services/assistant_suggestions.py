"""Normalize assistant output into a strict, reviewable field patch."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re

import httpx


FIELD_DEFINITIONS: dict[str, tuple[str, str]] = {
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


def _fallback_raw(content: str, gift_type_code: str) -> dict[str, object]:
    clean = re.sub(r"https?://\S+", "", content).strip()
    price_match = re.search(r"(?:¥|￥|约|价格|价)?\s*(\d+(?:\.\d{1,2})?)\s*元", content)
    price = float(price_match.group(1)) if price_match else None
    raw: dict[str, object] = {
        "recommendedGiftTypeCode": gift_type_code,
        "shortDescription": clean[:120] or "请结合来源补充礼物说明。",
        "whyTemplate": f"可以把{clean[:40] or '这份礼物'}送给合适的对象，请人工确认具体匹配关系。",
        "priceMin": price,
        "priceMax": price,
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
Return recommendedGiftTypeCode, shortDescription, priceMin, priceMax, isFree, whyTemplate,
recipientTypes[], occasions[], interests[], tags[], confidence, fieldConfidence, plus
productDetails {{genericProductName, materials[], personalizationMethods[], shippingRequired}}
or activityDetails {{activityCategory, serviceRegions[], durationMinutesMin,
durationMinutesMax, participantsMin, participantsMax, bookingRequired,
bookingLeadDaysMin, bookingLeadDaysMax}}. Use null or [] when unknown."""


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
    image_attachments: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    raw = _fallback_raw(content, gift_type_code)
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
                latest_content: str | list[dict[str, object]] = latest_payload
                if image_attachments:
                    latest_content = [{"type": "text", "text": latest_payload}]
                    latest_content.extend(
                        {"type": "image_url", "image_url": {"url": image["data"]}}
                        for image in image_attachments
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
                                "content": latest_content,
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
    confidence = (
        round(sum(float(item["confidence"]) for item in patches) / len(patches), 2)
        if patches
        else 0.0
    )
    return {
        "content": f"已整理出 {len(patches)} 条字段建议。请逐项审核后再写入表单。",
        "patches": patches,
        "confidence": confidence,
        "source": source,
    }
