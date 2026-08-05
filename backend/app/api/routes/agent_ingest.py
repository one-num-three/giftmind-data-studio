"""One-call gift analysis and draft ingestion for trusted collection agents."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal
from uuid import uuid4

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import SessionContext, get_db_session, require_session
from backend.app.models.assets import GiftImage
from backend.app.models.gift import Gift
from backend.app.schemas.gift import GiftCreateAdapter
from backend.app.services.assistant_suggestions import generate_assistant_result
from backend.app.services.gifts import DuplicateGiftError, create_gift
from backend.app.services.image_understanding import understand_images
from backend.app.services.source_extraction import extract_public_page, extract_urls

router = APIRouter(prefix="/api/agent", tags=["agent-ingest"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
ProtectedSession = Annotated[SessionContext, Depends(require_session)]

SUPPORTED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
SKILL_NAME = "giftmind-gift-ingest"
SKILL_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = PROJECT_ROOT / "skills" / SKILL_NAME


@router.get("/skill", name="giftmind_skill_metadata")
async def giftmind_skill_metadata(request: Request) -> dict[str, object]:
    """Return a public, non-secret description of the downloadable skill."""
    archive = _skill_archive()
    return {
        "name": SKILL_NAME,
        "version": SKILL_VERSION,
        "downloadUrl": str(request.url_for("download_giftmind_skill")),
        "sha256": hashlib.sha256(archive).hexdigest(),
        "sizeBytes": len(archive),
    }


@router.get("/skill/download", name="download_giftmind_skill")
async def download_giftmind_skill() -> Response:
    """Download the versioned Agent skill without exposing server secrets."""
    archive = _skill_archive()
    return Response(
        content=archive,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{SKILL_NAME}-{SKILL_VERSION}.zip"',
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/gifts/counts")
async def gift_counts(session: DatabaseSession, _auth: ProtectedSession) -> dict[str, object]:
    """Return current non-deleted gift counts by type and lifecycle status."""
    rows = (
        await session.execute(
            select(Gift.gift_type_code, Gift.status, func.count(Gift.id))
            .where(Gift.deleted_at.is_(None))
            .group_by(Gift.gift_type_code, Gift.status)
        )
    ).all()
    type_counts = {"product": 0, "activity": 0}
    status_counts = {"draft": 0, "active": 0, "inactive": 0}
    for gift_type, lifecycle_status, count in rows:
        number = int(count)
        if gift_type in type_counts:
            type_counts[gift_type] += number
        status_counts[lifecycle_status] = status_counts.get(lifecycle_status, 0) + number
    return {
        "productCount": type_counts["product"],
        "activityCount": type_counts["activity"],
        "totalCount": sum(type_counts.values()),
        "byStatus": status_counts,
    }


@router.post("/gifts/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_gift(
    request: Request,
    session: DatabaseSession,
    _auth: ProtectedSession,
    description: Annotated[str, Form(max_length=8000)] = "",
    gift_type_code: Annotated[Literal["auto", "product", "activity"], Form()] = "auto",
    lifecycle_status: Annotated[Literal["draft", "active", "inactive"], Form()] = "draft",
    source_urls_json: Annotated[str, Form(max_length=12000)] = "[]",
    known_fields_json: Annotated[str, Form(max_length=30000)] = "{}",
    images: Annotated[list[UploadFile] | None, File()] = None,
) -> dict[str, object]:
    """Analyze evidence, validate one typed gift, and persist it as one operation."""
    known_fields = _json_object(known_fields_json, "knownFieldsJson")
    explicit_urls = _json_string_list(source_urls_json, "sourceUrlsJson", limit=20)
    urls = _validated_urls([*explicit_urls, *extract_urls(description)])
    resolved_images = images or []
    if not description.strip() and not urls and not resolved_images and not known_fields:
        raise HTTPException(status_code=422, detail="请至少提供图片、链接、描述或已知字段")
    if len(resolved_images) > 4:
        raise HTTPException(status_code=422, detail="一次最多上传 4 张图片")

    with TemporaryDirectory(prefix="giftmind-agent-") as temp_dir:
        prepared_images = await _prepare_images(resolved_images, Path(temp_dir))
        source_refs = await _collect_sources(request, description, urls, prepared_images)
        selected_type = gift_type_code if gift_type_code in {"product", "activity"} else "product"
        result = await generate_assistant_result(
            content=description.strip() or "请根据提供的礼物资料完成结构化录入。",
            gift_type_code=selected_type,
            current_values=known_fields,
            history=[],
            source_refs=source_refs,
            api_key=request.app.state.settings.deepseek_api_key,
        )
        payload_data = _build_payload(
            result=result,
            known_fields=known_fields,
            requested_type=gift_type_code,
            lifecycle_status=lifecycle_status,
            source_urls=urls,
        )
        try:
            payload = GiftCreateAdapter.validate_python(payload_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INCOMPLETE_GIFT",
                    "message": "现有资料不足以生成可入库礼物，请补充返回的问题或已知字段。",
                    "questions": result.get("questions", []),
                    "errors": exc.errors(include_url=False),
                    "suggestedFields": payload_data,
                },
            ) from exc
        try:
            gift = await create_gift(session, payload)
        except DuplicateGiftError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_GIFT", "matches": [match.__dict__ for match in exc.matches]},
            ) from exc
        stored_images = await _store_images(request, session, str(gift.id), prepared_images, gift.short_description)

    return {
        "created": True,
        "gift": gift.model_dump(mode="json", by_alias=True),
        "images": stored_images,
        "analysis": {
            "source": result.get("source", "rule"),
            "confidence": result.get("confidence", 0),
            "suggestedFieldCount": len(result.get("patches", [])),
            "questions": result.get("questions", []),
            "sourceRefs": [_source_summary(item) for item in source_refs],
        },
    }


def _json_object(raw: str, field: str) -> dict[str, object]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"{field} 必须是合法 JSON") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail=f"{field} 必须是 JSON 对象")
    return value


def _json_string_list(raw: str, field: str, *, limit: int) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"{field} 必须是合法 JSON") from exc
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value) or len(value) > limit:
        raise HTTPException(status_code=422, detail=f"{field} 必须是最多 {limit} 项的字符串数组")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def _validated_urls(candidates: list[str]) -> list[str]:
    urls: list[str] = []
    for candidate in candidates:
        url = candidate.strip()
        if extract_urls(url) != [url]:
            raise HTTPException(status_code=422, detail=f"不是有效的公开 HTTP/HTTPS 链接：{candidate}")
        if url not in urls:
            urls.append(url)
    return urls


async def _prepare_images(images: list[UploadFile], temp_dir: Path) -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    for index, image in enumerate(images):
        mime_type = image.content_type or ""
        if mime_type not in SUPPORTED_IMAGES:
            raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、WebP 图片")
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="单张图片必须为 1B–8MB")
        suffix = SUPPORTED_IMAGES[mime_type]
        path = temp_dir / f"{index}{suffix}"
        path.write_bytes(content)
        prepared.append(
            {
                "name": Path(image.filename or f"gift-{index}{suffix}").name,
                "mimeType": mime_type,
                "suffix": suffix,
                "path": path,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return prepared


async def _collect_sources(
    request: Request,
    description: str,
    urls: list[str],
    images: list[dict[str, object]],
) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    if urls:
        async with httpx.AsyncClient() as client:
            for url in urls:
                sources.append(
                    await extract_public_page(
                        url,
                        client,
                        playwright_enabled=request.app.state.settings.playwright_enabled,
                        playwright_timeout_ms=request.app.state.settings.playwright_timeout_ms,
                        taobao_state_path=request.app.state.settings.taobao_state_path,
                    )
                )
    if images:
        sources.extend(await understand_images(images, request.app.state.settings))
    if description.strip():
        sources.append({"label": "Agent 提供的描述", "status": "ok", "text": description.strip()[:8000]})
    return sources or [{"label": "Agent 提供的已知字段", "status": "ok"}]


def _build_payload(
    *,
    result: dict[str, object],
    known_fields: dict[str, object],
    requested_type: str,
    lifecycle_status: str,
    source_urls: list[str],
) -> dict[str, object]:
    suggested: dict[str, object] = {}
    for patch in result.get("patches", []):
        if isinstance(patch, dict) and patch.get("path") and patch.get("value") is not None:
            _set_path(suggested, str(patch["path"]), patch["value"])
    merged = _deep_merge(suggested, known_fields)
    inferred_type = str(merged.get("giftTypeCode") or "product")
    gift_type = requested_type if requested_type in {"product", "activity"} else inferred_type
    if gift_type not in {"product", "activity"}:
        gift_type = "product"
    merged["giftTypeCode"] = gift_type
    merged["status"] = lifecycle_status
    merged.setdefault("confidenceLevel", _confidence_level(result.get("confidence")))
    known_urls = merged.get("sourceUrls") if isinstance(merged.get("sourceUrls"), list) else []
    merged["sourceUrls"] = list(dict.fromkeys([*map(str, known_urls), *source_urls]))
    merged.setdefault("aliases", [])
    merged.setdefault("isCustomizable", False)
    merged.setdefault("isBundle", False)
    merged.setdefault("bundleComponents", [])
    if gift_type == "product":
        details = merged.get("productDetails") if isinstance(merged.get("productDetails"), dict) else {}
        merged["productDetails"] = {
            "productForm": "physical",
            "shippingRequired": True,
            **details,
        }
        merged.pop("activityDetails", None)
    else:
        details = merged.get("activityDetails") if isinstance(merged.get("activityDetails"), dict) else {}
        merged["activityDetails"] = {"activityMode": "offline", **details}
        merged.pop("productDetails", None)
    return merged


def _set_path(target: dict[str, object], path: str, value: object) -> None:
    parts = path.split(".")
    cursor = target
    for part in parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            nested = {}
            cursor[part] = nested
        cursor = nested
    cursor[parts[-1]] = value


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _confidence_level(value: object) -> str:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0
    return "high" if confidence >= 0.8 else "medium" if confidence >= 0.55 else "low"


async def _store_images(
    request: Request,
    session: AsyncSession,
    gift_id: str,
    images: list[dict[str, object]],
    alt_text: str | None,
) -> list[dict[str, object]]:
    stored: list[dict[str, object]] = []
    directory = request.app.state.settings.upload_dir / "gifts" / gift_id
    directory.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(images):
        filename = f"{uuid4().hex}{image['suffix']}"
        relative = Path("gifts") / gift_id / filename
        (request.app.state.settings.upload_dir / relative).write_bytes(image["content"])  # type: ignore[arg-type]
        row = GiftImage(
            gift_id=gift_id,
            original_filename=str(image["name"]),
            stored_filename=relative.as_posix(),
            content_type=str(image["mimeType"]),
            sha256=str(image["sha256"]),
            file_size_bytes=len(image["content"]),  # type: ignore[arg-type]
            display_order=index,
            is_cover=index == 0,
            alt_text=alt_text,
        )
        session.add(row)
        await session.flush()
        stored.append(
            {
                "id": row.id,
                "filename": row.original_filename,
                "url": f"/uploads/{relative.as_posix()}",
                "isCover": row.is_cover,
            }
        )
    if images:
        await session.commit()
    return stored


def _source_summary(source: dict[str, object]) -> dict[str, object]:
    return {
        key: source.get(key)
        for key in ("label", "url", "status", "processor", "error")
        if source.get(key) not in (None, "")
    }


def _skill_archive() -> bytes:
    if not (SKILL_DIR / "SKILL.md").is_file():
        raise HTTPException(status_code=503, detail="GiftMind skill package is not installed on this server")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SKILL_DIR.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = Path(SKILL_NAME) / path.relative_to(SKILL_DIR)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2024, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".py" else 0o644) << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()
