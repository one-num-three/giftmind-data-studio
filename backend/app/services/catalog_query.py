"""Read the single eligible gift catalog used by the H5 planner."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.gift import ActivityDetail, Gift
from backend.app.schemas.planning import CatalogCandidate


async def load_active_catalog(session: AsyncSession) -> list[CatalogCandidate]:
    rows = (
        await session.execute(
            select(Gift).where(
                Gift.status == "active",
                Gift.deleted_at.is_(None),
                Gift.completeness_score >= 60,
            )
        )
    ).scalars().all()
    activity_ids = [gift.id for gift in rows if gift.gift_type_code == "activity"]
    activity_by_id: dict[str, ActivityDetail] = {}
    if activity_ids:
        details = (
            await session.execute(select(ActivityDetail).where(ActivityDetail.gift_id.in_(activity_ids)))
        ).scalars().all()
        activity_by_id = {detail.gift_id: detail for detail in details}

    return [_candidate(gift, activity_by_id.get(gift.id)) for gift in rows]


def _candidate(gift: Gift, activity: ActivityDetail | None) -> CatalogCandidate:
    kind = gift.gift_type_code
    category = "体验" if kind == "activity" else "组合" if gift.is_bundle else "定制" if gift.is_customizable else "实物"
    regions = list(activity.service_regions or []) if activity else []
    return CatalogCandidate(
        catalog_id=gift.id,
        name=gift.canonical_name,
        kind=kind,
        category=category,
        description=gift.short_description,
        emoji=gift.emoji or ("🎟️" if kind == "activity" else "🎁"),
        price_min=float(gift.price_min or 0),
        price_max=float(gift.price_max if gift.price_max is not None else gift.price_min or 0),
        currency=gift.currency,
        recipient_types=list(gift.recipient_types or []),
        relationship_stages=list(gift.relationship_stages or []),
        traits=list(gift.traits or []),
        interests=list(gift.interests or []),
        occasions=list(gift.occasions or []),
        desired_feelings=list(gift.desired_feelings or []),
        memory_hooks=list(gift.memory_hooks or []),
        tags=[*list(gift.tags or []), *list(gift.custom_tags or [])],
        taboo_flags=list(gift.taboo_flags or []),
        unsuitable_groups=list(gift.unsuitable_groups or []),
        lead_days_min=gift.lead_days_min or 0,
        lead_days_max=gift.lead_days_max if gift.lead_days_max is not None else gift.lead_days_min or 0,
        rush_available=gift.rush_available,
        why_template=gift.why_template,
        tip=gift.purchase_or_booking_tip,
        activity_mode=activity.activity_mode if activity else None,
        service_regions=regions,
        completeness_score=gift.completeness_score or 0,
    )
