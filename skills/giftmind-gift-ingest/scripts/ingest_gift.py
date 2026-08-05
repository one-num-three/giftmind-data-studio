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
from pathlib import Path
from typing import Any


SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze and create one GiftMind gift draft")
    parser.add_argument("--base-url", default=os.getenv("GIFTMIND_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--description", default="")
    parser.add_argument("--image", action="append", default=[])
    parser.add_argument("--source-url", action="append", default=[])
    parser.add_argument("--gift-type", choices=("auto", "product", "activity"), default="auto")
    parser.add_argument("--status", choices=("draft", "active", "inactive"), default="draft")
    parser.add_argument("--name")
    parser.add_argument("--price-min", type=float)
    parser.add_argument("--price-max", type=float)
    parser.add_argument("--color", action="append", default=[])
    parser.add_argument("--collector-notes")
    parser.add_argument("--known-json", help="Inline JSON object or path to a JSON file")
    parser.add_argument("--counts", action="store_true", help="Return current product/activity counts without ingesting")
    return parser.parse_args()


def load_known_fields(args: argparse.Namespace) -> dict[str, Any]:
    known: dict[str, Any] = {}
    if args.known_json:
        candidate = Path(args.known_json)
        raw = candidate.read_text(encoding="utf-8") if candidate.is_file() else args.known_json
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("--known-json must contain one JSON object")
        known.update(value)
    if args.name:
        known["canonicalName"] = args.name
    if args.price_min is not None:
        known["priceMin"] = args.price_min
    if args.price_max is not None:
        known["priceMax"] = args.price_max
    if args.collector_notes:
        known["collectorNotes"] = args.collector_notes
    if args.color:
        details = known.setdefault("productDetails", {})
        if not isinstance(details, dict):
            raise ValueError("knownFields.productDetails must be an object")
        details["colors"] = list(dict.fromkeys(args.color))
    return known


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
