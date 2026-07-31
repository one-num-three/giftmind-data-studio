"""Normalize assistant output into a strict, reviewable field patch."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from copy import deepcopy

import httpx

from backend.app.services.gift_type_inference import GiftTypeDecision, infer_gift_type

FIELD_DEFINITIONS: dict[str, tuple[str, str]] = {
    "canonicalName": ("标准名称", "text"),
    "giftTypeCode": ("礼物类型", "type"),
    "shortDescription": ("简短说明", "text"),
    "priceMin": ("最低价格", "number"),
    "priceMax": ("最高价格", "number"),
    "isFree": ("免费", "boolean"),
    "whyTemplate": ("送礼理由", "text"),
    "purchaseOrBookingTip": ("购买/预约提示", "text"),
    "ritualTip": ("铺垫与仪式提示", "text"),
    "pairingIdeas": ("贺卡/邀请文案方向", "text"),
    "recipientTypes": ("适合对象", "list"),
    "occasions": ("适合场景", "list"),
    "interests": ("兴趣标签", "list"),
    "tags": ("检索标签", "list"),
    "productDetails.genericProductName": ("通用商品名", "text"),
    "productDetails.materials": ("材质", "list"),
    "productDetails.colors": ("颜色", "list"),
    "productDetails.sizes": ("尺寸规格", "list"),
    "productDetails.variantNotes": ("规格备注", "text"),
    "productDetails.sizeClass": ("尺寸级别", "text"),
    "productDetails.packageDimensions": ("包装尺寸", "text"),
    "productDetails.personalizationMethods": ("定制方式", "list"),
    "productDetails.personalizationRequirements": ("定制要求", "text"),
    "productDetails.shippingRequired": ("需要配送", "boolean"),
    "productDetails.shippingNotes": ("配送说明", "text"),
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

_TEXT_SUGGESTION_FIELDS = {
    "canonicalName",
    "typeReason",
    "shortDescription",
    "whyTemplate",
    "bestScenarios",
    "unsuitableScenarios",
    "purchaseOrBookingTip",
    "ritualTip",
    "pairingIdeas",
}
_TEMPLATE_PLACEHOLDER_VALUES = {
    "recipient": "收礼人",
    "receiver": "收礼人",
    "relationship": "双方关系",
    "occasion": "节日、聚餐或朋友聚会",
    "gift_recipient": "收礼人",
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


def _is_measurement_only(value: object) -> bool:
    return bool(re.fullmatch(r"(?:\d+(?:\.\d+)?\s*)?(?:毫米|厘米|米|mm|cm|m|克|公斤|g|kg)", str(value).strip(), flags=re.IGNORECASE))


def _clean_name_value(value: object) -> str | None:
    """Keep a field name-like instead of letting a sentence or dimension leak in."""
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"^(?:这是|商品是|礼物是|名称是|请识别|帮我看看|帮我识别|一个|一款|这个|这款)\s*[：:，,\s]*", "", text)
    text = re.split(r"[，,。；;\n]|(?:直径|尺寸|规格|售价|价格|约为|大约是)", text, maxsplit=1)[0].strip(" ：:，,。")
    return text[:80] or None


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
    field_reasons = raw.get("fieldReasons")
    reason_map = field_reasons if isinstance(field_reasons, Mapping) else {}
    field_evidence = raw.get("fieldEvidence")
    evidence_map = field_evidence if isinstance(field_evidence, Mapping) else {}
    sources = _source_labels(source_refs)
    patches: list[dict[str, object]] = []
    for path, value in _flatten(raw).items():
        label, kind = FIELD_DEFINITIONS[path]
        normalized = _normalize_value(kind, value)
        if normalized is None:
            continue
        if path in {"canonicalName", "productDetails.genericProductName"}:
            normalized = _clean_name_value(normalized)
            if normalized is None:
                continue
        if path in {"canonicalName", "productDetails.genericProductName"} and _is_measurement_only(normalized):
            continue
        confidence = _clamp_confidence(confidence_map.get(path), overall)
        reason = reason_map.get(path)
        reason_text = str(reason).strip() if reason is not None else ""
        evidence = evidence_map.get(path)
        if isinstance(evidence, list):
            evidence_items = [str(item).strip() for item in evidence if str(item).strip()][:3]
        elif evidence is not None and str(evidence).strip():
            evidence_items = [str(evidence).strip()]
        else:
            evidence_items = []
        patches.append(
            {
                "path": path,
                "label": label,
                "value": deepcopy(normalized),
                "confidence": confidence,
                "reason": reason_text or None,
                "evidence": evidence_items,
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
    clean = _clean_user_content(content)
    first_source = next((item for item in source_refs or [] if item.get("status") == "ok"), {})
    source_title = str(first_source.get("title") or first_source.get("label") or "").strip()
    source_description = str(first_source.get("description") or first_source.get("text") or "").strip()
    display_name = _guess_name(clean, source_title)
    if clean in {"识别图片", "请识别图片", "分析图片", "看看这张图"} and source_description:
        display_name = _guess_name(source_description, "")
    detail_text = source_description or clean
    analysis_text = " ".join(part for part in (clean, source_title, source_description) if part)
    number_pattern = r"\d+(?:\.\d{1,2})?"
    price_range = re.search(
        rf"(?:¥|￥|约|预算|价格|价)?\s*({number_pattern})\s*(?:到|至|[-~～])\s*({number_pattern})\s*元",
        analysis_text,
    )
    price_match = re.search(rf"(?:¥|￥|约|价格|价)?\s*({number_pattern})\s*元", analysis_text)
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
        "shortDescription": _build_description(display_name, detail_text),
        "whyTemplate": None,
        "priceMin": price_min,
        "priceMax": price_max,
        "confidence": 0.42,
        "fieldConfidence": {
            "canonicalName": 0.78 if display_name else 0.0,
            "shortDescription": 0.76 if detail_text else 0.0,
            "priceMin": 0.68 if price_min is not None else 0.0,
            "priceMax": 0.68 if price_max is not None else 0.0,
        },
        "fieldReasons": {},
        "fieldEvidence": {},
    }
    if gift_type_code == "product":
        raw.update(
            {
                "purchaseOrBookingTip": "确认配送、兑换和到货时间，尽量保留收到礼物时的惊喜感。",
                "ritualTip": "可以先从对方近期的需要或兴趣自然铺垫，交付时再说明这是专门为他准备的。",
                "pairingIdeas": "可配一张手写贺卡，写下具体的喜欢与祝福；也可以在快递备注中留一句简短寄语。",
            }
        )
    else:
        raw.update(
            {
                "purchaseOrBookingTip": "先确认活动档期、地点、预约规则和取消政策，再把选择权留给对方。",
                "ritualTip": "先表达想和对方一起创造一段回忆，再用轻松语气发出邀请，明确时间可以一起调整。",
                "pairingIdeas": "可写一张活动邀请函或承诺券，例如“这次想把时间留给我们，你方便时我们一起去”。",
            }
        )
    if gift_type_code == "product":
        details, inferred = _infer_product_details(analysis_text)
        raw["productDetails"] = details
        match = _infer_matching_fields(analysis_text, display_name)
        raw.update(match)
        raw["fieldConfidence"].update({path: 0.74 for path in inferred})
        raw["fieldEvidence"].update({path: [evidence] for path, evidence in _evidence_for_product(analysis_text, details).items()})
        raw["fieldReasons"].update({path: "从你提供的名称或描述中直接识别。" for path in inferred})
        for field in ("recipientTypes", "occasions", "interests", "tags"):
            if raw.get(field):
                raw["fieldConfidence"][field] = 0.64
                raw["fieldReasons"][field] = "根据描述中的主题线索做的低置信推断，建议人工确认。"
                raw["fieldEvidence"][field] = match.get("whyEvidence") or ["描述中出现了相关主题线索。"]
    else:
        raw["activityDetails"] = {}
    if price_min is not None:
        raw["fieldEvidence"]["priceMin"] = [f"识别到价格提示：{price_min:g} 元"]
        raw["fieldEvidence"]["priceMax"] = [f"识别到价格提示：{price_max:g} 元"]
        raw["fieldReasons"]["priceMin"] = "来源中出现了价格数字，但仍需确认它是单件价还是其他价格。"
        raw["fieldReasons"]["priceMax"] = "来源中出现了价格数字，但仍需确认它是单件价还是其他价格。"
    raw["fieldEvidence"]["canonicalName"] = [display_name] if display_name else []
    raw["fieldEvidence"]["shortDescription"] = [detail_text[:160]] if detail_text else []
    raw["fieldReasons"]["canonicalName"] = "按名称或描述中的主体词整理，不把尺寸单位当作商品名。"
    raw["fieldReasons"]["shortDescription"] = "保留已提供的事实，不补写未提供的材质、价格或功能。"
    match = _infer_matching_fields(analysis_text, display_name)
    if match.get("whyTemplate"):
        raw["whyTemplate"] = match["whyTemplate"]
        raw["fieldConfidence"]["whyTemplate"] = 0.68
        raw["fieldEvidence"]["whyTemplate"] = match["whyEvidence"]
        raw["fieldReasons"]["whyTemplate"] = "根据描述中的对象线索和礼物用途做的低置信推断。"
    raw["followUpQuestions"] = _fallback_questions(analysis_text, gift_type_code, price_min)
    return raw


def _guess_name(clean: str, source_title: str) -> str:
    if (
        source_title
        and source_title not in {"用户描述", "用户上传图片", "商品详情", "网页来源", "商品链接"}
        and not source_title.startswith("http")
        and not re.match(r"^(?:图片|文件|附件)\s*[:：]", source_title)
    ):
        return source_title[:80]
    text = re.sub(r"^(?:这是|商品是|礼物是|名称是|请识别|帮我看看|帮我识别|OCR|图片描述|识别结果|商品标题)[：:，,\s]*", "", clean, flags=re.IGNORECASE)
    text = re.split(r"[，,。；;\n]", text, maxsplit=1)[0].strip()
    text = re.sub(r"^(?:一个|一款|这个|这款)\s*", "", text)
    text = re.split(r"(?:直径|尺寸|规格|售价|价格|约为|大约是)", text, maxsplit=1)[0].strip(" ：:，,。")
    return text[:80]


def _clean_user_content(content: str) -> str:
    """Keep the described gift and remove assistant instructions from fallback text."""
    clean = re.sub(r"https?://\S+", "", content).strip()
    clean = re.split(
        r"(?:请(?:帮我|你)?(?:识别|分析|填写|补充|整理)|请完整填写|帮我(?:识别|分析|填写)|希望你)",
        clean,
        maxsplit=1,
    )[0].strip(" ：:，,。；;\n")
    return clean


def _build_description(name: str, detail_text: str) -> str | None:
    if not detail_text:
        return name or None
    text = re.sub(r"\s+", " ", detail_text).strip()
    if name and text == name:
        return f"{name}，具体材质、价格和适用对象待确认。"
    if name:
        for prefix in ("一个", "一款", "这个", "这款"):
            if text.startswith(prefix + name):
                remainder = text[len(prefix) + len(name) :].strip(" ：:，,。")
                if remainder:
                    return f"{name}，{remainder.rstrip('。')}。"
                break
    return text[:160]


def _infer_product_details(text: str) -> tuple[dict[str, object], list[str]]:
    details: dict[str, object] = {}
    inferred: list[str] = []
    categories = ("冰箱贴", "书签", "徽章", "钥匙扣", "明信片", "笔记本", "保温杯", "水杯", "香薰", "帆布袋", "玩偶")
    category = next((item for item in categories if item in text), None)
    if category:
        details["genericProductName"] = category
        inferred.append("productDetails.genericProductName")
    materials = [name for name in ("黄铜", "金属", "铁质", "磁铁", "木质", "陶瓷", "玻璃", "皮革", "棉麻", "纸张", "塑料") if name in text]
    if materials:
        details["materials"] = materials
        inferred.append("productDetails.materials")
    sizes = [f"{number} {unit}" for number, unit in re.findall(r"(?:直径|尺寸|长宽高)?\s*(\d+(?:\.\d+)?)\s*(厘米|cm|毫米|mm)", text, flags=re.IGNORECASE)]
    if sizes:
        details["sizes"] = sizes
        inferred.append("productDetails.sizes")
    return details, inferred


def _evidence_for_product(text: str, details: Mapping[str, object]) -> dict[str, str]:
    evidence: dict[str, str] = {}
    if details.get("genericProductName"):
        evidence["productDetails.genericProductName"] = f"描述中出现“{details['genericProductName']}”"
    if details.get("materials"):
        evidence["productDetails.materials"] = "描述中出现：" + "、".join(map(str, details["materials"]))
    if details.get("sizes"):
        evidence["productDetails.sizes"] = "描述中出现：" + "、".join(map(str, details["sizes"]))
    return evidence


def _infer_matching_fields(text: str, name: str) -> dict[str, object]:
    institution_match = re.search(r"([\u4e00-\u9fa5]{2,}?(?:大学|学院|学校))", text)
    institution = institution_match.group(1) if institution_match else ""
    institution = re.sub(r"^(?:一个|一款|这个|这款)", "", institution)
    result: dict[str, object] = {"recipientTypes": [], "occasions": [], "interests": [], "tags": []}
    if "校徽" in text or "校园" in text:
        result["recipientTypes"] = [f"{institution}校友" if institution else "校友", "在校学生"]
        result["occasions"] = ["毕业", "纪念"]
        result["interests"] = ["校园文化", "收藏"]
        result["tags"] = ["校园文创", "纪念品", "小体积"]
        target = institution or "校园"
        result["whyTemplate"] = f"适合送给{target}校友或在校学生，适合作为毕业、返校或纪念场景中的小礼物。"
        result["whyEvidence"] = [f"描述中出现“{target}”和“校徽”"]
    elif any(keyword in text for keyword in ("博物馆", "文创", "景区")):
        result["recipientTypes"] = ["喜欢文化旅行的人", "收藏爱好者"]
        result["occasions"] = ["旅行纪念", "纪念"]
        result["interests"] = ["文化", "旅行", "收藏"]
        result["tags"] = ["文创", "纪念品"]
        result["whyEvidence"] = ["描述中出现“博物馆”“文创”或“景区”等文化旅行线索"]
    return result


def _fallback_questions(text: str, gift_type_code: str, price_min: float | None) -> list[str]:
    questions: list[str] = []
    if price_min is None:
        questions.append("单件实际售价或常见价格区间是多少？")
    if gift_type_code == "product" and not any(keyword in text for keyword in ("材质", "金属", "铁质", "磁铁", "木质", "陶瓷", "玻璃", "皮革")):
        questions.append("材质是什么？如果不确定，可以先留空。")
    if not any(keyword in text for keyword in ("送给", "适合", "对象", "校友", "学生", "老师", "生日", "毕业", "纪念", "场景")):
        questions.append("最希望推荐给哪类人，或用于什么送礼场景？")
    return questions[:3]


def _assistant_prompt(gift_type_code: str, type_decision: GiftTypeDecision | None = None) -> str:
    type_specific = (
        "productDetails: { productForm, genericProductName, materials[], colors[], sizes[], "
        "variantNotes, sizeClass, packageDimensions, personalizationMethods[], "
        "personalizationRequirements, shippingRequired, shippingNotes }"
        if gift_type_code == "product"
        else
        "activityDetails: { activityMode, activityCategory, serviceRegions[], "
        "durationMinutesMin, durationMinutesMax, participantsMin, participantsMax, "
        "pricingUnit, bookingRequired, bookingLeadDaysMin, bookingLeadDaysMax, "
        "validityDays, includedItems[], excludedItems[], indoorOutdoor }"
    )
    type_reason = type_decision.reason if type_decision else "按当前选择的类型处理。"
    return f"""You are a professional AI gift advisor helping a Chinese gift-data collection team. Return one valid JSON object only, without Markdown or extra commentary. The hard expected type is {gift_type_code}. The deterministic type decision is: {type_reason}.

The only boundary between Goods and Activity is whether the gift giver participates together with the recipient. Goods means the giver does not need to show up and, after delivery, the recipient owns or uses it alone. Goods includes physical products, single-person experiences or services such as a solo spa voucher, individual diving lesson, personal gym card, or electronic redemption code. For Goods, advise on creating an unboxing or receiving surprise and produce a custom-card or delivery-message direction. Activity means the giver must participate with the recipient, in a two-person or group experience such as shared camping, pottery, a concert, a meal, or an escape room. For Activity, advise on a friendly invitation, schedule coordination, avoiding social pressure, and an invitation letter or promise-coupon direction.

Never classify an experience as Activity merely because it is an experience: first look for shared participation such as 一起、共同、双人、多人、陪你、和朋友、我们、相约 or 邀请. If the recipient is explicitly alone, or the giver is only sending a voucher or item, use Goods. If participation is not stated, do not invent that the giver will attend; keep the selected type and clearly ask the collector to confirm it.

Use the guidance fields according to the type: for Goods, purchaseOrBookingTip should cover delivery, timing, unboxing, or redemption; ritualTip should explain a natural surprise setup; pairingIdeas should include 2-3 short card or delivery-message directions. For Activity, purchaseOrBookingTip should cover booking and coordinating dates; ritualTip should explain how to invite without pressure; pairingIdeas should include 2-3 invitation-letter, promise-coupon, or opening-script directions. Do not fill activity-only guidance for Goods or goods-only guidance for Activity.

Type is a hard constraint. recommendedGiftTypeCode MUST be exactly {gift_type_code}; never return the opposite type because of a stale or default UI selection. If the input describes a shared activity with the giver participating (for example 一起露营、双人观星、共同体验课程、一起看演出), use activity and fill activityDetails. If the experience is for the recipient alone, use product. If participation is not stated, keep the hard expected type and ask for confirmation rather than inventing a shared plan. If the input describes an item people buy, own, consume, ship, or use (for example 礼盒、冰箱贴、书签、镜头、帐篷、底料、茶叶), use product and fill productDetails. Activity and product details are mutually exclusive: do not put booking, duration, participants, or service regions into productDetails; do not put materials, shipping, sizes, or generic product names into activityDetails.

Analyze the latest message, conversation, source extracts, and current form values. Use natural Simplified Chinese. shortDescription should be a useful 25-60 character summary. whyTemplate must contain 4-6 distinct bullet points separated by newlines, with every line starting with '- '. Cover different angles such as the gift's concrete features, the recipient's likely preferences, a suitable occasion, the emotional or practical value, and a useful usage or pairing suggestion; do not repeat the same reason. Each point should be a complete, specific sentence of about 15-40 Chinese characters. Never output template placeholders such as {{recipient}}, {{occasion}}, or {{relationship}}; use natural words such as 收礼人 or 朋友聚会 instead. Never invent a merchant, exact URL, address, or unsupported fact. Do not copy instructions into canonicalName. Price is an estimated CNY range and must be null when the source does not support it. Fill applicable fields and use null or [] when unknown.

Return: canonicalName, recommendedGiftTypeCode (product|activity), typeReason, subcategoryCode, shortDescription, whyTemplate, priceMin, priceMax, isFree, recipientTypes[], relationshipStages[], ageRanges[], traits[], interests[], occasions[], desiredFeelings[], memoryHooks[], tags[], customTags[], bestScenarios, unsuitableScenarios, purchaseOrBookingTip, ritualTip, pairingIdeas, confidence (0 to 1), followUpQuestions[] with at most 3 important missing facts, and {type_specific}."""


def _missing_information_questions(
    current_values: Mapping[str, object],
    gift_type_code: str,
    suggested_values: Mapping[str, object] | None = None,
) -> list[str]:
    suggested = suggested_values or {}

    def present(key: str) -> bool:
        return _has_substantive_value(current_values.get(key)) or _has_substantive_value(suggested.get(key))

    candidates: list[str] = []
    if not present("canonicalName"):
        candidates.append("这份礼物的标准名称是什么？")
    if not present("priceMin") and not present("priceMax"):
        candidates.append("它通常的价格区间是多少？如果免费也请说明。")
    if not present("recipientTypes"):
        candidates.append("它最适合送给哪些对象？")
    if not present("occasions"):
        candidates.append("它最适合生日、纪念日、感谢还是其他场景？")
    details = current_values.get(f"{gift_type_code}Details") or suggested.get(f"{gift_type_code}Details")
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


def _has_substantive_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _merge_model_with_fallback(
    model_raw: Mapping[str, object],
    fallback_raw: Mapping[str, object],
) -> dict[str, object]:
    """Keep verified rule facts when a model response is sparse."""
    merged = deepcopy(dict(fallback_raw))
    for key, value in model_raw.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            nested = dict(merged[key])  # type: ignore[arg-type]
            for nested_key, nested_value in value.items():
                if _has_substantive_value(nested_value):
                    nested[nested_key] = deepcopy(nested_value)
            merged[key] = nested
        elif _has_substantive_value(value):
            merged[key] = _clean_suggestion_text(value, format_reasons=key == "whyTemplate") if key in _TEXT_SUGGESTION_FIELDS else deepcopy(value)
    return merged


def _clean_suggestion_text(value: object, *, format_reasons: bool = False) -> object:
    if not isinstance(value, str):
        return value

    def replace_placeholder(match: re.Match[str]) -> str:
        name = match.group(1).lower()
        return _TEMPLATE_PLACEHOLDER_VALUES.get(name, "对方")

    cleaned = re.sub(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}", replace_placeholder, value).strip()
    return _format_reason_points(cleaned) if format_reasons else cleaned


def _enforce_type_contract(
    raw: Mapping[str, object],
    type_decision: GiftTypeDecision,
) -> dict[str, object]:
    """Make the selected type and its detail section mutually exclusive."""
    normalized = deepcopy(dict(raw))
    normalized["recommendedGiftTypeCode"] = type_decision.code
    normalized["typeReason"] = type_decision.reason
    if type_decision.code == "product":
        normalized["activityDetails"] = {}
        if not isinstance(normalized.get("productDetails"), Mapping):
            normalized["productDetails"] = {}
    else:
        normalized["productDetails"] = {}
        if not isinstance(normalized.get("activityDetails"), Mapping):
            normalized["activityDetails"] = {}
    return normalized


def _format_reason_points(text: str) -> str:
    lines = [line.strip() for line in re.split(r"\r?\n+", text) if line.strip()]
    if len(lines) == 1:
        lines = [part.strip() for part in re.split(r"(?<=[。！？；])\s*", lines[0]) if part.strip()]
    lines = [re.sub(r"^(?:[-*•]\s*|\d+[.)、]\s*)", "", line) for line in lines[:6]]
    if 4 <= len(lines) <= 6:
        return "\n".join(f"- {line}" for line in lines)
    return text


async def generate_assistant_result(
    *,
    content: str,
    gift_type_code: str,
    current_values: dict[str, object],
    history: list[dict[str, str]],
    source_refs: list[dict[str, object]],
    api_key: str | None,
) -> dict[str, object]:
    evidence_parts = [content, str(current_values.get("canonicalName") or ""), str(current_values.get("shortDescription") or "")]
    for source in source_refs:
        evidence_parts.extend(
            str(source.get(key) or "")[:2000]
            for key in ("title", "description", "text")
        )
    type_decision = infer_gift_type("\n".join(evidence_parts), gift_type_code)
    effective_type = type_decision.code
    raw = _fallback_raw(content, effective_type, source_refs)
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
            async with httpx.AsyncClient(timeout=45) as client:
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
                        "thinking": {"type": "disabled"},
                        "temperature": 0.1,
                        "messages": [
                            {"role": "system", "content": _assistant_prompt(effective_type, type_decision)},
                            {
                                "role": "user",
                                "content": latest_payload,
                            },
                        ],
                    },
                )
                response.raise_for_status()
                model_raw = _parse_json_object(response.json()["choices"][0]["message"]["content"])
                raw = _merge_model_with_fallback(model_raw, raw)
                source = "deepseek"
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            source = "rule"
    raw = _enforce_type_contract(raw, type_decision)
    patches = suggestion_to_patches(raw, source_refs)
    model_questions = raw.get("followUpQuestions")
    questions = (
        [str(question).strip() for question in model_questions if str(question).strip()][:3]
        if isinstance(model_questions, list)
        else []
    )
    if type_decision.activity_clues and not type_decision.shared_participation_clues and not type_decision.single_recipient_clues and not type_decision.product_clues:
        questions.insert(0, "送礼人会和收礼人一起参加吗？如果会，请明确写出“一起、双人或共同参加”；否则按商品处理。")
        questions = questions[:3]
    for question in _missing_information_questions(current_values, effective_type, raw):
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
