"""Idempotently import the H5 editorial seed catalog into Data Studio.

Run from the Data Studio repository root:
    python -m backend.scripts.import_h5_seed ../giftmind-h5/data/giftmind-seed-catalog.json --status active
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.database import create_engine
from backend.app.models.gift import Gift
from backend.app.schemas.gift import GiftCreateAdapter
from backend.app.services.gifts import create_gift


def seed_to_gift_payload(record: dict[str, Any], *, status: str = "draft") -> dict[str, Any]:
    kind = record.get("kind") or "product"
    fit = record.get("fit") or {}
    pricing = record.get("pricing") or {}
    planning = record.get("planning") or {}
    acquisition = record.get("acquisition") or {}
    constraints = record.get("constraints") or {}
    source = record.get("evidence") or {}
    price_min = pricing.get("min", record.get("priceLow", 0))
    price_max = pricing.get("max", record.get("priceHigh", price_min))
    common = {
        "giftTypeCode": kind,
        "canonicalName": record["name"],
        "shortDescription": record.get("description") or record.get("why"),
        "status": status,
        "emoji": record.get("emoji") or ((record.get("media") or {}).get("cover") or {}).get("value"),
        "recipientTypes": fit.get("recipients") or record.get("recipients") or ["*"],
        "traits": fit.get("traits") or record.get("traits") or [],
        "occasions": fit.get("occasions") or record.get("occasions") or ["*"],
        "tags": fit.get("tags") or record.get("tags") or [],
        "priceMin": price_min,
        "priceMax": price_max,
        "leadDaysMin": planning.get("recommendedLeadDays", record.get("leadDays", 0)),
        "leadDaysMax": planning.get("recommendedLeadDays", record.get("leadDays", 0)),
        "rushAvailable": planning.get("recommendedLeadDays", record.get("leadDays", 0)) <= 2,
        "tabooFlags": constraints.get("avoidWhen") or record.get("avoid") or [],
        "whyTemplate": record.get("why") or record.get("description") or "适合作为一份认真准备的礼物。",
        "purchaseOrBookingTip": record.get("tip"),
        "sourceNotes": source.get("note") or "从 GiftMind H5 editorial seed 导入。",
        "sourceUrls": [source["sourceUrl"]] if source.get("sourceUrl") else [],
        "confidenceLevel": "editorial_seed",
    }
    if kind == "activity":
        common["activityDetails"] = {
            "activityMode": "online" if acquisition.get("fulfillment") == "digital_delivery" else "offline",
            "activityCategory": record.get("format") or "experience",
            "durationMinutesMin": 60,
            "durationMinutesMax": 180,
            "participantsMin": 1,
            "participantsMax": 2,
            "pricingUnit": pricing.get("basis") or "per_booking",
            "bookingRequired": True,
            "bookingLeadDaysMin": common["leadDaysMin"],
            "bookingLeadDaysMax": common["leadDaysMax"],
        }
    else:
        digital = record.get("format") == "digital_product"
        customizable = record.get("format") == "custom_product"
        common["isCustomizable"] = customizable
        common["productDetails"] = {
            "productForm": "digital" if digital else "physical",
            "genericProductName": record["name"],
            "materials": ["数字内容"] if digital else ["以实际商品为准"],
            "personalizationMethods": ["按页面选项定制"] if customizable else [],
            "shippingRequired": not digital,
            "digitalDeliveryMethod": "在线交付" if digital else None,
        }
    return common


async def import_catalog(path: Path, *, status: str) -> tuple[int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise TypeError("seed catalog must contain a records array")
    settings = get_settings()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    imported = skipped = 0
    async with factory() as session:
        for record in records:
            values = seed_to_gift_payload(record, status=status)
            exists = await session.scalar(
                select(func.count(Gift.id)).where(
                    Gift.gift_type_code == values["giftTypeCode"],
                    func.lower(Gift.canonical_name) == values["canonicalName"].strip().lower(),
                )
            )
            if exists:
                skipped += 1
                continue
            await create_gift(session, GiftCreateAdapter.validate_python(values))
            imported += 1
    await engine.dispose()
    return imported, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--status", choices=("draft", "active"), default="draft")
    args = parser.parse_args()
    imported, skipped = asyncio.run(import_catalog(args.path.resolve(), status=args.status))
    print(f"Imported {imported}; skipped existing {skipped}.")


if __name__ == "__main__":
    main()
