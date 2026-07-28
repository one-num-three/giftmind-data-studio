"""Persist, retrieve, and recycle typed gifts."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.assets import GiftImage
from backend.app.models.gift import (
    ActivityDetail,
    ActivityOffer,
    Gift,
    GiftBundleComponent,
    ProductDetail,
    ProductOffer,
)
from backend.app.models.operations import AuditEvent
from backend.app.schemas.gift import (
    ActivityGiftCreate,
    BundleComponentInput,
    GiftRead,
    ProductGiftCreate,
)
from backend.app.services.completeness import calculate_completeness
from backend.app.services.duplicates import DuplicateMatch, find_duplicates


GiftPayload = ProductGiftCreate | ActivityGiftCreate


class GiftNotFoundError(Exception):
    """Raised when an operation requires a missing (or non-active) gift."""


class DuplicateGiftError(Exception):
    """Raised when a normalized canonical name or alias is already in use."""

    def __init__(self, matches: list[DuplicateMatch]) -> None:
        self.matches = matches


async def create_gift(session: AsyncSession, payload: GiftPayload) -> GiftRead:
    """Create a typed gift after blocking exact normalized duplicates."""
    matches = await find_duplicates(session, payload.canonical_name, payload.aliases)
    exact_matches = [match for match in matches if match.exact]
    if exact_matches:
        raise DuplicateGiftError(exact_matches)
    gift = Gift(**_gift_values(payload))
    session.add(gift)
    await session.flush()
    await _replace_detail_and_components(session, gift, payload)
    await _set_completeness(session, gift)
    _audit(session, "gift.created", gift)
    await session.commit()
    return await _read_gift(session, gift)


async def update_gift(session: AsyncSession, gift_id: UUID, payload: GiftPayload) -> GiftRead:
    """Replace a typed gift while preserving the database's type-detail invariant."""
    gift = await _active_gift(session, gift_id)
    if gift.gift_type_code != payload.gift_type_code:
        raise ValueError("gift type cannot be changed")
    matches = await find_duplicates(
        session, payload.canonical_name, payload.aliases, exclude_gift_id=gift.id
    )
    exact_matches = [match for match in matches if match.exact]
    if exact_matches:
        raise DuplicateGiftError(exact_matches)
    for field, value in _gift_values(payload).items():
        setattr(gift, field, value)
    await _replace_detail_and_components(session, gift, payload)
    await _set_completeness(session, gift)
    _audit(session, "gift.updated", gift)
    await session.commit()
    return await _read_gift(session, gift)


async def copy_gift(session: AsyncSession, gift_id: UUID) -> GiftRead:
    """Clone a gift while clearing all verification state from the new record."""
    source = await _active_gift(session, gift_id)
    product_detail, activity_detail, components = await _related(session, source)
    values = {column.name: getattr(source, column.name) for column in Gift.__table__.columns}
    for key in ("id", "created_at", "updated_at", "deleted_at", "completeness_score", "verified_at"):
        values.pop(key, None)
    values["canonical_name"] = f"{source.canonical_name}（副本）"
    copy = Gift(**values)
    session.add(copy)
    await session.flush()
    if product_detail:
        session.add(ProductDetail(**_copy_columns(product_detail, "gift_id", gift_id=copy.id)))
    if activity_detail:
        session.add(ActivityDetail(**_copy_columns(activity_detail, "gift_id", gift_id=copy.id)))
    for component in components:
        session.add(GiftBundleComponent(**_copy_columns(component, "id", "bundle_gift_id", gift_id=copy.id)))
    await _copy_offers_without_channel_state(session, source.id, copy.id, source.gift_type_code)
    await _set_completeness(session, copy)
    _audit(session, "gift.copied", copy, {"source_gift_id": source.id})
    await session.commit()
    return await _read_gift(session, copy)


async def soft_delete_gift(session: AsyncSession, gift_id: UUID) -> None:
    gift = await _active_gift(session, gift_id)
    gift.deleted_at = datetime.now(UTC)
    _audit(session, "gift.soft_deleted", gift)
    await session.commit()


async def restore_gift(session: AsyncSession, gift_id: UUID) -> GiftRead:
    gift = await _deleted_gift(session, gift_id)
    gift.deleted_at = None
    _audit(session, "gift.restored", gift)
    await session.commit()
    return await _read_gift(session, gift)


async def purge_gift(session: AsyncSession, gift_id: UUID) -> None:
    gift = await _deleted_gift(session, gift_id)
    await session.execute(
        delete(GiftBundleComponent).where(
            or_(
                GiftBundleComponent.bundle_gift_id == gift.id,
                GiftBundleComponent.component_gift_id == gift.id,
            )
        )
    )
    _audit(session, "gift.purged", gift)
    await session.delete(gift)
    await session.commit()


async def get_gift(session: AsyncSession, gift_id: UUID, *, include_deleted: bool = False) -> GiftRead:
    gift = await (_deleted_or_active_gift(session, gift_id) if include_deleted else _active_gift(session, gift_id))
    return await _read_gift(session, gift)


async def list_gifts(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    include_deleted: bool = False,
    q: str | None = None,
    status: str | None = None,
    gift_type: str | None = None,
    carrier_or_mode: str | None = None,
    is_customizable: bool | None = None,
    is_bundle: bool | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    min_completeness: int | None = None,
    has_image: bool | None = None,
    has_offer: bool | None = None,
    verified: bool | None = None,
) -> tuple[list[GiftRead], int]:
    """Return a filtered, paginated collection or its recycle-bin counterpart."""
    filters = [Gift.deleted_at.is_not(None) if include_deleted else Gift.deleted_at.is_(None)]
    if q:
        filters.append(func.lower(Gift.canonical_name).like(f"%{q.lower()}%"))
    if status:
        filters.append(Gift.status == status)
    if gift_type:
        filters.append(Gift.gift_type_code == gift_type)
    if is_customizable is not None:
        filters.append(Gift.is_customizable.is_(is_customizable))
    if is_bundle is not None:
        filters.append(Gift.is_bundle.is_(is_bundle))
    if price_min is not None:
        filters.append(Gift.price_max >= price_min)
    if price_max is not None:
        filters.append(Gift.price_min <= price_max)
    if min_completeness is not None:
        filters.append(Gift.completeness_score >= min_completeness)
    if verified is not None:
        filters.append(Gift.verified_at.is_not(None) if verified else Gift.verified_at.is_(None))
    if has_image is not None:
        exists = select(GiftImage.id).where(GiftImage.gift_id == Gift.id).exists()
        filters.append(exists if has_image else ~exists)
    if has_offer is not None:
        product_exists = select(ProductOffer.id).where(ProductOffer.gift_id == Gift.id).exists()
        activity_exists = select(ActivityOffer.id).where(ActivityOffer.gift_id == Gift.id).exists()
        exists = product_exists | activity_exists
        filters.append(exists if has_offer else ~exists)
    if carrier_or_mode:
        filters.append(
            (select(ProductDetail.gift_id).where(
                ProductDetail.gift_id == Gift.id, ProductDetail.product_form == carrier_or_mode
            ).exists())
            | (select(ActivityDetail.gift_id).where(
                ActivityDetail.gift_id == Gift.id, ActivityDetail.activity_mode == carrier_or_mode
            ).exists())
        )
    count = await session.scalar(select(func.count()).select_from(Gift).where(*filters))
    gifts = (await session.scalars(
        select(Gift).where(*filters).order_by(Gift.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()
    return [await _read_gift(session, gift) for gift in gifts], count or 0


def _gift_values(payload: GiftPayload) -> dict:
    values = payload.model_dump(
        mode="python", exclude={"gift_type_code", "product_details", "activity_details", "bundle_components"}
    )
    values["gift_type_code"] = payload.gift_type_code
    values["source_urls"] = [str(url) for url in values["source_urls"]]
    return values


async def _replace_detail_and_components(session: AsyncSession, gift: Gift, payload: GiftPayload) -> None:
    await session.execute(delete(ProductDetail).where(ProductDetail.gift_id == gift.id))
    await session.execute(delete(ActivityDetail).where(ActivityDetail.gift_id == gift.id))
    await session.execute(delete(GiftBundleComponent).where(GiftBundleComponent.bundle_gift_id == gift.id))
    if isinstance(payload, ProductGiftCreate):
        session.add(ProductDetail(gift_id=gift.id, **payload.product_details.model_dump(mode="json")))
    else:
        session.add(ActivityDetail(gift_id=gift.id, **payload.activity_details.model_dump(mode="json")))
    for component in payload.bundle_components:
        session.add(GiftBundleComponent(bundle_gift_id=gift.id, **_component_values(component)))
    await session.flush()


async def _set_completeness(session: AsyncSession, gift: Gift) -> None:
    product, activity, _ = await _related(session, gift)
    gift.product_details = product
    gift.activity_details = activity
    gift.completeness_score = calculate_completeness(gift).score
    await session.flush()


async def _read_gift(session: AsyncSession, gift: Gift) -> GiftRead:
    product, activity, components = await _related(session, gift)
    values = {column.name: getattr(gift, column.name) for column in Gift.__table__.columns}
    values["product_details"] = _detail_values(product)
    values["activity_details"] = _detail_values(activity)
    values["bundle_components"] = [_component_values_from_model(component) for component in components]
    return GiftRead.model_validate(values)


async def _related(
    session: AsyncSession, gift: Gift
) -> tuple[ProductDetail | None, ActivityDetail | None, list[GiftBundleComponent]]:
    product = await session.get(ProductDetail, gift.id)
    activity = await session.get(ActivityDetail, gift.id)
    components = (await session.scalars(
        select(GiftBundleComponent).where(GiftBundleComponent.bundle_gift_id == gift.id).order_by(GiftBundleComponent.display_order)
    )).all()
    return product, activity, components


async def _active_gift(session: AsyncSession, gift_id: UUID) -> Gift:
    gift = await session.scalar(select(Gift).where(Gift.id == str(gift_id), Gift.deleted_at.is_(None)))
    if gift is None:
        raise GiftNotFoundError
    return gift


async def _deleted_gift(session: AsyncSession, gift_id: UUID) -> Gift:
    gift = await session.scalar(select(Gift).where(Gift.id == str(gift_id), Gift.deleted_at.is_not(None)))
    if gift is None:
        raise GiftNotFoundError
    return gift


async def _deleted_or_active_gift(session: AsyncSession, gift_id: UUID) -> Gift:
    gift = await session.get(Gift, str(gift_id))
    if gift is None:
        raise GiftNotFoundError
    return gift


def _detail_values(detail: ProductDetail | ActivityDetail | None) -> dict | None:
    if detail is None:
        return None
    return {
        column.name: getattr(detail, column.name)
        for column in detail.__table__.columns
        if column.name not in {"gift_id", "created_at", "updated_at"}
    }


def _component_values(component: BundleComponentInput) -> dict:
    return component.model_dump(mode="json")


def _component_values_from_model(component: GiftBundleComponent) -> dict:
    return {
        column.name: getattr(component, column.name)
        for column in GiftBundleComponent.__table__.columns
        if column.name not in {"id", "bundle_gift_id"}
    }


def _copy_columns(model: object, *excluded: str, gift_id: str) -> dict:
    values = {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns  # type: ignore[attr-defined]
        if column.name not in {*excluded, "created_at", "updated_at"}
    }
    if "gift_id" in excluded:
        values["gift_id"] = gift_id
    if "bundle_gift_id" in excluded:
        values["bundle_gift_id"] = gift_id
    return values


async def _copy_offers_without_channel_state(
    session: AsyncSession, source_id: str, copy_id: str, gift_type: str
) -> None:
    if gift_type == "product":
        offers = (await session.scalars(select(ProductOffer).where(ProductOffer.gift_id == source_id))).all()
        for offer in offers:
            values = _copy_columns(offer, "id", "gift_id", gift_id=copy_id)
            values.update({"verified_at": None, "stock_status": None, "active": False})
            session.add(ProductOffer(**values))
    else:
        offers = (await session.scalars(select(ActivityOffer).where(ActivityOffer.gift_id == source_id))).all()
        for offer in offers:
            values = _copy_columns(offer, "id", "gift_id", gift_id=copy_id)
            values.update({"verified_at": None, "availability_status": None, "active": False})
            session.add(ActivityOffer(**values))


def _audit(session: AsyncSession, event_type: str, gift: Gift, payload: dict | None = None) -> None:
    session.add(AuditEvent(event_type=event_type, entity_type="gift", entity_id=gift.id, payload_json=payload))
