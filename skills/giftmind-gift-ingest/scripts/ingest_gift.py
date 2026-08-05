#!/usr/bin/env python3
"""Submit mixed gift evidence to the GiftMind Agent ingestion endpoint."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp"}
LOCAL_MODE_MIN_SERVER_VERSION = (1, 1, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze and create one GiftMind gift draft")
    parser.add_argument("--base-url", default=os.getenv("GIFTMIND_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--description", default="")
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument("--source-url", action="append", default=[])
    parser.add_argument("--gift-type", choices=("auto", "product", "activity"), default="auto")
    parser.add_argument("--status", choices=("draft", "active", "inactive"), default="draft")
    parser.add_argument(
        "--analysis-mode",
        choices=("local", "cloud"),
        default="local",
        help="local skips server-side extraction and DeepSeek; cloud enables server analysis",
    )
    parser.add_argument("--name")
    parser.add_argument("--price-min", type=float)
    parser.add_argument("--price-max", type=float)
    parser.add_argument("--color", action="append", default=[])
    parser.add_argument("--material", action="append", default=[])
    parser.add_argument("--size", action="append", default=[])
    parser.add_argument("--generic-product-name")
    parser.add_argument("--variant-notes")
    parser.add_argument("--source-notes")
    parser.add_argument("--specifications-json", help="Inline JSON object or path to a JSON file")
    parser.add_argument("--taobao-shop-name")
    parser.add_argument("--taobao-item-id")
    parser.add_argument("--taobao-sku", action="append", default=[], metavar="DIMENSION=VALUE")
    parser.add_argument("--taobao-price", type=float, help="Exact selected-SKU detail-page price in CNY")
    parser.add_argument("--taobao-observed-at", help="ISO-8601 detail-page observation time with timezone")
    parser.add_argument("--collector-notes")
    parser.add_argument("--known-json", help="Inline JSON object or path to a JSON file")
    parser.add_argument("--counts", action="store_true", help="Return current product/activity counts without ingesting")
    return parser.parse_args()


def load_known_fields(args: argparse.Namespace) -> dict[str, Any]:
    known: dict[str, Any] = {}
    if args.known_json:
        known.update(load_json_object(args.known_json, "--known-json"))
    if args.name:
        known["canonicalName"] = args.name
    if args.taobao_price is not None:
        if args.taobao_price < 0:
            raise ValueError("--taobao-price must be non-negative")
        if args.price_min is not None and args.price_min != args.taobao_price:
            raise ValueError("--price-min conflicts with --taobao-price")
        if args.price_max is not None and args.price_max != args.taobao_price:
            raise ValueError("--price-max conflicts with --taobao-price")
        known["priceMin"] = args.taobao_price
        known["priceMax"] = args.taobao_price
    else:
        if args.price_min is not None:
            known["priceMin"] = args.price_min
        if args.price_max is not None:
            known["priceMax"] = args.price_max
    if args.collector_notes:
        known["collectorNotes"] = args.collector_notes
    details = product_details(known)
    if args.generic_product_name:
        details["genericProductName"] = args.generic_product_name
    if args.material:
        details["materials"] = unique(args.material)
    if args.color:
        details["colors"] = unique(args.color)
    if args.size:
        details["sizes"] = unique(args.size)
    if args.variant_notes:
        details["variantNotes"] = args.variant_notes
    specifications = load_specifications(args, details)
    taobao_evidence = load_taobao_evidence(args)
    if taobao_evidence:
        specifications["taobaoEvidence"] = taobao_evidence
        known["sourceNotes"] = merge_notes(known.get("sourceNotes"), args.source_notes, taobao_source_note(taobao_evidence))
    elif args.source_notes:
        known["sourceNotes"] = merge_notes(known.get("sourceNotes"), args.source_notes)
    if not details:
        known.pop("productDetails", None)
    return known


def load_json_object(raw_or_path: str, label: str) -> dict[str, Any]:
    candidate = Path(raw_or_path)
    raw = candidate.read_text(encoding="utf-8") if candidate.is_file() else raw_or_path
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def product_details(known: dict[str, Any]) -> dict[str, Any]:
    details = known.setdefault("productDetails", {})
    if not isinstance(details, dict):
        raise ValueError("knownFields.productDetails must be an object")
    return details


def load_specifications(args: argparse.Namespace, details: dict[str, Any]) -> dict[str, Any]:
    existing = details.get("specifications")
    if existing is None:
        specifications: dict[str, Any] = {}
    elif isinstance(existing, dict):
        specifications = dict(existing)
    else:
        if args.specifications_json or has_taobao_args(args):
            raise ValueError("productDetails.specifications must be an object for structured enrichment")
        return {}
    if args.specifications_json:
        specifications.update(load_json_object(args.specifications_json, "--specifications-json"))
    if specifications or args.specifications_json or has_taobao_args(args):
        details["specifications"] = specifications
    return specifications


def load_taobao_evidence(args: argparse.Namespace) -> dict[str, Any]:
    if not has_taobao_args(args):
        return {}
    selected_sku: dict[str, str] = {}
    for raw in args.taobao_sku:
        dimension, separator, value = raw.partition("=")
        if not separator or not dimension.strip() or not value.strip():
            raise ValueError("--taobao-sku must use DIMENSION=VALUE")
        selected_sku[dimension.strip()] = value.strip()
    observed_at = args.taobao_observed_at
    if observed_at:
        validate_iso_timestamp(observed_at)
    evidence: dict[str, Any] = {"platform": "taobao"}
    if args.taobao_shop_name:
        evidence["shopName"] = args.taobao_shop_name
    if args.taobao_item_id:
        evidence["itemId"] = args.taobao_item_id
    if selected_sku:
        evidence["selectedSku"] = selected_sku
    if args.taobao_price is not None:
        if not selected_sku:
            raise ValueError("--taobao-price requires at least one --taobao-sku DIMENSION=VALUE")
        if not observed_at:
            raise ValueError("--taobao-price requires --taobao-observed-at with a timezone")
        evidence["observedPriceCny"] = args.taobao_price
        evidence["priceEvidence"] = "detail-sku"
    if observed_at:
        evidence["observedAt"] = observed_at
    return evidence


def has_taobao_args(args: argparse.Namespace) -> bool:
    return any(
        (
            args.taobao_shop_name,
            args.taobao_item_id,
            args.taobao_sku,
            args.taobao_price is not None,
            args.taobao_observed_at,
        )
    )


def validate_iso_timestamp(value: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("--taobao-observed-at must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("--taobao-observed-at must include a timezone")


def taobao_source_note(evidence: dict[str, Any]) -> str:
    parts = ["淘宝实证"]
    if evidence.get("shopName"):
        parts.append(f"店铺={evidence['shopName']}")
    if evidence.get("itemId"):
        parts.append(f"itemId={evidence['itemId']}")
    selected_sku = evidence.get("selectedSku")
    if isinstance(selected_sku, dict) and selected_sku:
        parts.append("SKU=" + ", ".join(f"{key}={value}" for key, value in selected_sku.items()))
    if evidence.get("observedPriceCny") is not None:
        parts.append(f"详情页价格=CNY {evidence['observedPriceCny']:g}")
    if evidence.get("observedAt"):
        parts.append(f"采集时间={evidence['observedAt']}")
    return "；".join(parts)


def merge_notes(*values: Any) -> str:
    notes = [str(value).strip() for value in values if value is not None and str(value).strip()]
    return "\n".join(dict.fromkeys(notes))


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def encode_multipart(fields: dict[str, str], image_paths: list[str]) -> tuple[bytes, str]:
    boundary = f"giftmind-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for raw_path in image_paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime_type not in SUPPORTED_MIME:
            raise ValueError(f"Unsupported image type: {path.name}")
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError(f"Image exceeds 8 MB: {path.name}")
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="images"; filename="{path.name}"\r\n'.encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def request_json(opener: urllib.request.OpenerDirector, request: urllib.request.Request) -> dict[str, Any]:
    try:
        with opener.open(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = {"detail": body or exc.reason}
        print(json.dumps({"status": exc.code, **detail}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2) from exc


def version_tuple(value: object) -> tuple[int, int, int]:
    try:
        parts = [int(part) for part in str(value).split(".")[:3]]
    except ValueError:
        return (0, 0, 0)
    return tuple((parts + [0, 0, 0])[:3])  # type: ignore[return-value]


def ensure_local_mode_supported(opener: urllib.request.OpenerDirector, base_url: str) -> None:
    metadata = request_json(
        opener,
        urllib.request.Request(f"{base_url}/api/agent/skill", method="GET"),
    )
    server_version = version_tuple(metadata.get("version"))
    if server_version < LOCAL_MODE_MIN_SERVER_VERSION:
        required = ".".join(map(str, LOCAL_MODE_MIN_SERVER_VERSION))
        actual = str(metadata.get("version") or "unknown")
        raise ValueError(
            f"Server {actual} does not support local analysis mode; deploy GiftMind {required}+ "
            "or explicitly use --analysis-mode cloud"
        )


def main() -> int:
    args = parse_args()
    passcode = os.getenv("GIFTMIND_TEAM_PASSCODE", "")
    if not passcode:
        print("GIFTMIND_TEAM_PASSCODE is required", file=sys.stderr)
        return 2
    if len(args.image) > 4:
        print("At most four --image arguments are allowed", file=sys.stderr)
        return 2
    try:
        known_fields = load_known_fields(args)
        if not args.counts and not args.description.strip() and not args.image and not args.source_url and not known_fields:
            raise ValueError("Provide a description, image, source URL, or known field")
        fields = {
            "description": args.description,
            "gift_type_code": args.gift_type,
            "lifecycle_status": args.status,
            "analysis_mode": args.analysis_mode,
            "source_urls_json": json.dumps(args.source_url, ensure_ascii=False),
            "known_fields_json": json.dumps(known_fields, ensure_ascii=False),
        }
        body, content_type = encode_multipart(fields, args.image)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    base_url = args.base_url.rstrip("/")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    if args.analysis_mode == "local":
        try:
            ensure_local_mode_supported(opener, base_url)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    login_body = json.dumps({"passcode": passcode}).encode("utf-8")
    request_json(
        opener,
        urllib.request.Request(
            f"{base_url}/api/session/login",
            data=login_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
    )
    if args.counts:
        result = request_json(
            opener,
            urllib.request.Request(f"{base_url}/api/agent/gifts/counts", method="GET"),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    result = request_json(
        opener,
        urllib.request.Request(
            f"{base_url}/api/agent/gifts/ingest",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        ),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
