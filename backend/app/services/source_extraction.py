"""Bounded extraction of public web pages used as assistant source context."""

from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
import json
import re
import socket
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx


URL_PATTERN = re.compile(r"https?://[^\s<>'\"\]\[{}]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,!?;:，。！？；：、)]}）】》"
MAX_URLS = 3
MAX_BYTES = 1024 * 1024
Resolver = Callable[..., list]


def extract_urls(text: str) -> list[str]:
    found: list[str] = []
    for match in URL_PATTERN.findall(text):
        url = match.rstrip(TRAILING_PUNCTUATION)
        if url and url not in found:
            found.append(url)
        if len(found) == MAX_URLS:
            break
    return found


def is_public_http_url(url: str, resolver: Resolver = socket.getaddrinfo) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = resolver(hostname, port, type=socket.SOCK_STREAM)
        if not addresses:
            return False
        for entry in addresses:
            address = entry[4][0]
            if not ipaddress.ip_address(address).is_global:
                return False
        return True
    except (OSError, ValueError):
        return False


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.description = ""
        self.text_parts: list[str] = []
        self.structured_data: list[dict] = []
        self._hidden_depth = 0
        self._in_title = False
        self._in_json_ld = False
        self._json_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        lowered = tag.lower()
        if lowered in {"style", "noscript"}:
            self._hidden_depth += 1
        elif lowered == "script":
            if "ld+json" in attributes.get("type", "").lower():
                self._in_json_ld = True
                self._json_parts = []
            else:
                self._hidden_depth += 1
        elif lowered == "title":
            self._in_title = True
        elif lowered == "meta":
            name = attributes.get("name", "").lower()
            prop = attributes.get("property", "").lower()
            if name == "description" or prop in {"og:description", "twitter:description"}:
                if not self.description:
                    self.description = attributes.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1
        elif lowered == "script":
            if self._in_json_ld:
                self._consume_json_ld("".join(self._json_parts))
                self._in_json_ld = False
                self._json_parts = []
            elif self._hidden_depth:
                self._hidden_depth -= 1
        elif lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_json_ld:
            self._json_parts.append(data)
        elif self._in_title:
            self.title_parts.append(text)
        elif not self._hidden_depth:
            self.text_parts.append(text)

    def _consume_json_ld(self, raw: str) -> None:
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if isinstance(candidate, dict):
                graph = candidate.get("@graph")
                if isinstance(graph, list):
                    self.structured_data.extend(item for item in graph if isinstance(item, dict))
                else:
                    self.structured_data.append(candidate)


def _price_hints(*values: str) -> list[str]:
    pattern = re.compile(r"(?:¥|￥|CNY|RMB|价格|价)?\s*(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
    hints: list[str] = []
    for value in values:
        for match in pattern.findall(value):
            if match not in hints:
                hints.append(match)
            if len(hints) == 10:
                return hints
    return hints


async def extract_public_page(
    url: str,
    client: httpx.AsyncClient,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> dict[str, object]:
    original_url = url
    current_url = url
    try:
        for _redirect in range(4):
            if not is_public_http_url(current_url, resolver=resolver):
                return {"url": original_url, "label": original_url, "status": "blocked"}
            response = await client.get(
                current_url,
                headers={"User-Agent": "GiftMindDataStudio/1.0"},
                follow_redirects=False,
                timeout=10,
            )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    break
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return {
                    "url": original_url,
                    "resolvedUrl": current_url,
                    "label": original_url,
                    "status": "unsupported",
                }
            content = await response.aread()
            if len(content) > MAX_BYTES:
                return {
                    "url": original_url,
                    "resolvedUrl": current_url,
                    "label": original_url,
                    "status": "too_large",
                }
            encoding = response.encoding or "utf-8"
            html = content.decode(encoding, errors="replace")
            parser = _PageParser()
            parser.feed(html)
            title = " ".join(parser.title_parts).strip()
            text = " ".join(parser.text_parts)
            structured = parser.structured_data[:10]
            structured_text = json.dumps(structured, ensure_ascii=False)
            return {
                "url": original_url,
                "resolvedUrl": current_url,
                "label": title or urlparse(current_url).hostname or original_url,
                "status": "ok",
                "title": title,
                "description": parser.description,
                "text": text[:12000],
                "structuredData": structured,
                "priceHints": _price_hints(text, structured_text),
            }
        return {"url": original_url, "label": original_url, "status": "redirect_limit"}
    except (httpx.HTTPError, OSError, UnicodeError, ValueError) as error:
        return {
            "url": original_url,
            "label": original_url,
            "status": "error",
            "error": type(error).__name__,
        }

