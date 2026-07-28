"""Authenticated API routes for the typed gift collection and recycle bin."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import SessionContext, get_db_session, require_session
from backend.app.schemas.gift import GiftBulkStatusUpdate, GiftCreate, GiftPurgeConfirmation, GiftRead
from backend.app.services.duplicates import find_duplicates, scan_duplicate_pairs
from backend.app.services.gifts import (
    DuplicateGiftError,
    GiftNotFoundError,
    bulk_update_gift_status,
    copy_gift,
    create_gift,
    get_gift,
    list_gifts,
    purge_gift,
    restore_gift,
    soft_delete_gift,
    update_gift,
)


router = APIRouter(prefix="/api", tags=["gifts"])
ProtectedSession = Annotated[SessionContext, Depends(require_session)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/gifts/duplicates")
async def duplicate_check(
    canonical_name: Annotated[str, Query(alias="canonicalName")],
    session: DatabaseSession,
    _auth: ProtectedSession,
    aliases: list[str] = Query(default=[]),
) -> dict:
    matches = await find_duplicates(session, canonical_name, aliases)
    return {"matches": [match.__dict__ for match in matches]}


@router.get("/gifts")
async def list_active_gifts(
    session: DatabaseSession,
    _auth: ProtectedSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 50,
    q: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    gift_type: Annotated[str | None, Query(alias="giftType")] = None,
    carrier_or_mode: Annotated[str | None, Query(alias="carrierOrMode")] = None,
    is_customizable: Annotated[bool | None, Query(alias="isCustomizable")] = None,
    is_bundle: Annotated[bool | None, Query(alias="isBundle")] = None,
    price_min: Annotated[float | None, Query(alias="priceMin")] = None,
    price_max: Annotated[float | None, Query(alias="priceMax")] = None,
    min_completeness: Annotated[int | None, Query(alias="minCompleteness", ge=0, le=100)] = None,
    has_image: Annotated[bool | None, Query(alias="hasImage")] = None,
    has_offer: Annotated[bool | None, Query(alias="hasOffer")] = None,
    verified: bool | None = None,
    deleted: Literal["exclude", "only"] = "exclude",
) -> dict:
    items, total = await list_gifts(
        session, page=page, page_size=page_size, q=q, status=status_filter, gift_type=gift_type,
        carrier_or_mode=carrier_or_mode, is_customizable=is_customizable, is_bundle=is_bundle,
        price_min=price_min, price_max=price_max, min_completeness=min_completeness,
        has_image=has_image, has_offer=has_offer, verified=verified, deleted=deleted,
    )
    return {"items": [item.model_dump(mode="json", by_alias=True) for item in items], "total": total, "page": page, "pageSize": page_size}


@router.patch("/gifts/bulk/status")
async def update_selected_gift_status(
    payload: dict, session: DatabaseSession, _auth: ProtectedSession
) -> dict[str, int]:
    try:
        change = GiftBulkStatusUpdate.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    affected = await bulk_update_gift_status(session, change.gift_ids, change.status)
    return {"affected": affected}


@router.post("/gifts", response_model=GiftRead, status_code=status.HTTP_201_CREATED)
async def create_typed_gift(payload: GiftCreate, session: DatabaseSession, _auth: ProtectedSession) -> GiftRead:
    try:
        return await create_gift(session, payload)
    except DuplicateGiftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"matches": [match.__dict__ for match in exc.matches]}) from exc


@router.get("/gifts/duplicate-groups")
async def duplicate_groups(session: DatabaseSession, _auth: ProtectedSession) -> dict[str, object]:
    pairs = await scan_duplicate_pairs(session)
    return {"pairs": pairs, "count": len(pairs)}


@router.get("/gifts/{gift_id}", response_model=GiftRead)
async def read_gift(gift_id: UUID, session: DatabaseSession, _auth: ProtectedSession) -> GiftRead:
    try:
        return await get_gift(session, gift_id)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc


@router.put("/gifts/{gift_id}", response_model=GiftRead)
async def replace_gift(gift_id: UUID, payload: GiftCreate, session: DatabaseSession, _auth: ProtectedSession) -> GiftRead:
    try:
        return await update_gift(session, gift_id, payload)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc
    except DuplicateGiftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"matches": [match.__dict__ for match in exc.matches]}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/gifts/{gift_id}/copy", response_model=GiftRead, status_code=status.HTTP_201_CREATED)
async def copy_existing_gift(gift_id: UUID, session: DatabaseSession, _auth: ProtectedSession) -> GiftRead:
    try:
        return await copy_gift(session, gift_id)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc


@router.delete("/gifts/{gift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def recycle_gift(gift_id: UUID, session: DatabaseSession, _auth: ProtectedSession) -> Response:
    try:
        await soft_delete_gift(session, gift_id)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recycle-bin/gifts")
async def list_recycled_gifts(
    session: DatabaseSession, _auth: ProtectedSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 50,
) -> dict:
    items, total = await list_gifts(session, page=page, page_size=page_size, deleted="only")
    return {"items": [item.model_dump(mode="json", by_alias=True) for item in items], "total": total, "page": page, "pageSize": page_size}


@router.post("/recycle-bin/gifts/{gift_id}/restore", response_model=GiftRead)
async def restore_recycled_gift(gift_id: UUID, session: DatabaseSession, _auth: ProtectedSession) -> GiftRead:
    try:
        return await restore_gift(session, gift_id)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc


@router.delete("/recycle-bin/gifts/{gift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_recycled_gift(
    gift_id: UUID,
    confirmation: GiftPurgeConfirmation,
    session: DatabaseSession,
    _auth: ProtectedSession,
) -> Response:
    try:
        gift = await get_gift(session, gift_id, include_deleted=True)
        if gift.canonical_name != confirmation.canonical_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Gift name confirmation does not match")
        await purge_gift(session, gift_id)
    except GiftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
