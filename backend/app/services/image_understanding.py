"""Turn uploaded images into text before invoking the text-only DeepSeek model."""

from __future__ import annotations

import asyncio
import base64
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import httpx


class ImageSettings(Protocol):
    vision_api_key: str | None
    vision_base_url: str | None
    vision_model: str | None


@lru_cache(maxsize=1)
def _paddle_engine():
    from paddleocr import PaddleOCR  # type: ignore[import-not-found]

    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _collect_rec_texts(value: object) -> list[str]:
    texts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "rec_texts" and isinstance(item, list):
                texts.extend(str(text).strip() for text in item if str(text).strip())
            else:
                texts.extend(_collect_rec_texts(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            texts.extend(_collect_rec_texts(item))
    else:
        payload = getattr(value, "json", None)
        if payload is not None:
            texts.extend(_collect_rec_texts(payload() if callable(payload) else payload))
        result = getattr(value, "res", None)
        if result is not None:
            texts.extend(_collect_rec_texts(result))
    return texts


def _local_paddle_ocr(path: Path) -> str:
    """Run PaddleOCR when the optional OCR extra is installed."""
    try:
        results = _paddle_engine().predict(str(path))
    except (ImportError, ModuleNotFoundError, RuntimeError, AttributeError):
        return ""
    unique: list[str] = []
    for text in _collect_rec_texts(results):
        if text not in unique:
            unique.append(text)
    return "\n".join(unique)


async def _vision_description(
    path: Path,
    mime_type: str,
    settings: ImageSettings,
    client: httpx.AsyncClient,
) -> str:
    if not settings.vision_api_key or not settings.vision_base_url or not settings.vision_model:
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    response = await client.post(
        f"{settings.vision_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.vision_api_key}"},
        json={
            "model": settings.vision_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请客观描述这张礼物资料图中的商品或活动、材质、包装、可见文字与其他可用于资料录入的细节。不要猜测看不见的信息。",
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                    ],
                }
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return str(content).strip()


async def understand_images(
    images: list[dict[str, object]],
    settings: ImageSettings,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, object]]:
    """Return bounded OCR/vision source references for one assistant turn."""
    owns_client = client is None
    resolved_client = client or httpx.AsyncClient()
    references: list[dict[str, object]] = []
    try:
        for image in images[:4]:
            path = Path(str(image["path"]))
            name = Path(str(image.get("name") or path.name)).name
            mime_type = str(image.get("mimeType") or "image/jpeg")
            ocr_text = await asyncio.to_thread(_local_paddle_ocr, path)
            description = ""
            vision_error = ""
            try:
                description = await _vision_description(path, mime_type, settings, resolved_client)
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                vision_error = "视觉模型暂时不可用"
            parts = []
            if ocr_text:
                parts.append(f"OCR 文字：\n{ocr_text[:6000]}")
            if description:
                parts.append(f"图片描述：\n{description[:4000]}")
            references.append(
                {
                    "label": f"图片：{name}",
                    "status": "ok" if parts else "unavailable",
                    "ocrText": ocr_text[:6000],
                    "description": description[:4000],
                    "text": "\n\n".join(parts),
                    "processor": "paddleocr+vision" if ocr_text and description else "paddleocr" if ocr_text else "vision" if description else "none",
                    "error": "" if parts else vision_error or "未配置可用的 PaddleOCR 或视觉模型",
                }
            )
    finally:
        if owns_client:
            await resolved_client.aclose()
    return references
