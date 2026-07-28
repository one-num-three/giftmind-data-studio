"""Authenticated aggregate maintenance signals for the data-studio dashboard."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import SessionContext, get_db_session, require_session
from backend.app.models.assets import GiftImage
from backend.app.models.gift import ActivityOffer, Gift, ProductOffer
from backend.app.models.operations import AuditEvent
from backend.app.schemas.common import APIModel


router = APIRouter(prefix="/api", tags=["dashboard"])
ProtectedSession = Annotated[SessionContext, Depends(require_session)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
STALE_CHANNEL_AGE = timedelta(days=30)


class AuditEventRead(APIModel):
    event_type: str
    entity_type: str
    entity_id: str | None
    payload_json: dict | list | None
    created_at: datetime


class DashboardSummary(APIModel):
    total: int
    complete: int
    drafts: int
    needs_review: int
    inactive: int
    product_count: int
    activity_count: int
    missing_images: int
    missing_sources: int
    stale_channels: int
    possible_duplicates: int
    recent_changes: list[AuditEventRead]


@router.get("/dashboard", response_model=DashboardSummary)
async def read_dashboard(session: DatabaseSession, _auth: ProtectedSession) -> DashboardSummary:
    """Return maintenance counts for non-deleted product and activity records."""
    gifts = (await session.scalars(
        select(Gift).where(Gift.deleted_at.is_(None)).order_by(Gift.updated_at.desc())
    )).all()
    active_ids = [gift.id for gift in gifts]
    image_gift_ids = set((await session.scalars(
        select(GiftImage.gift_id).where(GiftImage.gift_id.in_(active_ids))
    )).all()) if active_ids else set()
    stale_before = datetime.now(UTC) - STALE_CHANNEL_AGE
    product_offers = (await session.scalars(
        select(ProductOffer).where(ProductOffer.gift_id.in_(active_ids), ProductOffer.active.is_(True))
    )).all() if active_ids else []
    activity_offers = (await session.scalars(
        select(ActivityOffer).where(ActivityOffer.gift_id.in_(active_ids), ActivityOffer.active.is_(True))
    )).all() if active_ids else []
    recent_events = (await session.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10)
    )).all()

    return DashboardSummary(
        total=len(gifts),
        complete=sum(gift.completeness_score == 100 and gift.status != "inactive" for gift in gifts),
        drafts=sum(gift.status == "draft" for gift in gifts),
        needs_review=sum((gift.completeness_score or 0) < 100 and gift.status != "inactive" for gift in gifts),
        inactive=sum(gift.status == "inactive" for gift in gifts),
        product_count=sum(gift.gift_type_code == "product" for gift in gifts),
        activity_count=sum(gift.gift_type_code == "activity" for gift in gifts),
        missing_images=sum(gift.id not in image_gift_ids for gift in gifts),
        missing_sources=sum(not gift.source_urls for gift in gifts),
        stale_channels=sum(
            _is_stale_channel(offer.verified_at, stale_before)
            for offer in [*product_offers, *activity_offers]
        ),
        possible_duplicates=_possible_duplicate_count(gifts),
        recent_changes=[
            AuditEventRead(
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                payload_json=event.payload_json,
                created_at=event.created_at,
            )
            for event in recent_events
        ],
    )


def _possible_duplicate_count(gifts: list[Gift]) -> int:
    """Count records sharing a normalized canonical name or alias."""
    identifiers: dict[str, set[str]] = {}
    for gift in gifts:
        for value in [gift.canonical_name, *gift.aliases]:
            normalized = value.strip().casefold()
            if normalized:
                identifiers.setdefault(normalized, set()).add(gift.id)
    duplicate_ids = set().union(*(ids for ids in identifiers.values() if len(ids) > 1)) if identifiers else set()
    return len(duplicate_ids)


def _is_stale_channel(verified_at: datetime | None, stale_before: datetime) -> bool:
    """Compare SQLite's naive timestamps with the UTC-aware dashboard threshold."""
    if verified_at is None:
        return True
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    return verified_at < stale_before
