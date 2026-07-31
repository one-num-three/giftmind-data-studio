"""Bounded extraction of public web pages used as assistant source context."""

from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - only used when the browser runtime is absent
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None


URL_PATTERN = re.compile(r"https?://[^\s<>'\"\]\[{}]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,!?;:，。！？；：、)]}）】》"
MAX_URLS = 3
MAX_BYTES = 1024 * 1024
MAX_RENDERED_TEXT = 12000
TAOBAO_HOST_SUFFIXES = ("taobao.com", "tmall.com", "tmall.hk", "tb.cn")
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


def is_taobao_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        return any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in TAOBAO_HOST_SUFFIXES)
    except ValueError:
        return False


def is_taobao_product_url(url: str) -> bool:
    """Return whether a URL looks like a public Taobao/Tmall product page."""

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if not is_taobao_host(url):
            return False
        # Taobao share links use hosts such as e.tb.cn and s.tb.cn and do not
        # contain the final /item.htm path until the browser follows redirect.
        if hostname == "tb.cn" or hostname.endswith(".tb.cn"):
            return True
        return (
            hostname.startswith("item.")
            or hostname.startswith("detail.")
            or "/item.htm" in parsed.path
            or "/i" in parsed.path
        )
    except ValueError:
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


def _normalize_rendered_text(value: str) -> str:
    return " ".join(value.split())[:MAX_RENDERED_TEXT]


async def _first_visible_text(page: object, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if await locator.count() == 0:
                continue
            value = (await locator.inner_text(timeout=2500)).strip()
            if value:
                return _normalize_rendered_text(value)
        except Exception:
            continue
    return ""


async def _meta_content(page: object, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if await locator.count() == 0:
                continue
            value = str(await locator.get_attribute("content") or "").strip()
            if value:
                return _normalize_rendered_text(value)
        except Exception:
            continue
    return ""


async def _extract_taobao_page(
    url: str,
    *,
    resolver: Resolver,
    timeout_ms: int,
    state_path: Path | None = None,
) -> dict[str, object]:
    """Read a public Taobao/Tmall page in a headless browser.

    This intentionally returns text-only context. Image, video, and font requests
    are aborted before the page is rendered, so the assistant never downloads or
    stores product imagery from the source page.
    """

    if async_playwright is None:
        return {
            "url": url,
            "label": url,
            "status": "browser_unavailable",
            "error": "Playwright 未安装或浏览器运行时不可用",
        }

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context_options: dict[str, object] = {
                "locale": "zh-CN",
                "user_agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36 GiftMind/1.0"
                ),
                "viewport": {"width": 1280, "height": 900},
            }
            if state_path is not None and state_path.is_file():
                context_options["storage_state"] = str(state_path)
            context = await browser.new_context(
                **context_options,
            )
            page = await context.new_page()

            async def block_non_text_assets(route: object) -> None:
                resource_type = route.request.resource_type  # type: ignore[attr-defined]
                if resource_type in {"image", "media", "font"}:
                    await route.abort()  # type: ignore[attr-defined]
                else:
                    await route.continue_()  # type: ignore[attr-defined]

            await page.route("**/*", block_non_text_assets)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8_000))
            except PlaywrightTimeoutError:
                pass
            await page.wait_for_timeout(800)

            resolved_url = page.url
            # The initial URL is restricted to official Taobao hosts. Keep
            # official Taobao redirects usable even when a server-side DNS
            # environment reports a non-global test address; non-Taobao
            # redirects still go through the SSRF guard.
            if not is_public_http_url(resolved_url, resolver=resolver) and not is_taobao_host(resolved_url):
                return {
                    "url": url,
                    "resolvedUrl": resolved_url,
                    "label": url,
                    "status": "blocked",
                }

            status_code = response.status if response is not None else 200
            body_text = _normalize_rendered_text(await page.locator("body").inner_text(timeout=5000))
            title = await _first_visible_text(page, ["h1", "title"])
            if not title:
                title = await _meta_content(page, ["meta[property='og:title']"])
            if not title:
                title = await page.title()
            description = await _meta_content(
                page,
                [
                    "meta[name='description']",
                    "meta[property='og:description']",
                    "meta[name='twitter:description']",
                ],
            )
            structured: list[dict[str, object]] = []
            for raw in await page.locator("script[type='application/ld+json']").all_text_contents():
                try:
                    value = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                candidates = value if isinstance(value, list) else [value]
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    graph = candidate.get("@graph")
                    if isinstance(graph, list):
                        structured.extend(item for item in graph if isinstance(item, dict))
                    else:
                        structured.append(candidate)
            structured = structured[:10]
            structured_text = json.dumps(structured, ensure_ascii=False)
            challenge_text = f"{title} {body_text}".lower()
            resolved_host = (urlparse(resolved_url).hostname or "").lower().rstrip(".")
            login_page = resolved_host in {"login.taobao.com", "passport.taobao.com", "login.tmall.com"} or title.strip() in {"登录", "淘宝登录"}
            if login_page or any(marker in challenge_text for marker in ("请先登录", "登录后查看", "登录淘宝", "立即登录")):
                page_status = "login_required"
                error = "淘宝页面要求登录，请在数据工具中打开淘宝登录，完成一次登录并保存服务器状态后，再重新解析。"
            elif any(marker in challenge_text for marker in ("请完成验证", "滑动验证", "安全验证", "访问受限", "人机验证", "captcha", "verify")):
                page_status = "challenge"
                error = "淘宝要求人工完成验证，请在服务器浏览器中完成验证后保存登录状态，再重新解析。"
            elif status_code >= 400:
                page_status = "error"
                error = f"淘宝页面返回 HTTP {status_code}。"
            elif not any((title, description, body_text, structured)):
                page_status = "login_required"
                error = "没有抓到淘宝商品文字，通常是短链未展开、需要登录或遇到人工验证。请先保存淘宝登录状态后重试。"
            else:
                page_status = "ok"
                error = None
            return {
                "url": url,
                "resolvedUrl": resolved_url,
                "label": title or urlparse(resolved_url).hostname or url,
                "status": page_status,
                "title": title,
                "description": description,
                "text": body_text,
                "structuredData": structured,
                "priceHints": _price_hints(body_text, description, structured_text),
                "extractionMode": "playwright-text-only",
                **({"error": error} if error else {}),
            }
    except PlaywrightTimeoutError:
        return {"url": url, "label": url, "status": "timeout", "error": "页面加载超时"}
    except Exception as error:
        return {
            "url": url,
            "label": url,
            "status": "browser_error",
            "error": type(error).__name__,
        }


async def extract_public_page(
    url: str,
    client: httpx.AsyncClient,
    *,
    resolver: Resolver = socket.getaddrinfo,
    playwright_enabled: bool = True,
    playwright_timeout_ms: int = 20_000,
    taobao_state_path: Path | None = None,
) -> dict[str, object]:
    original_url = url
    current_url = url
    try:
        if playwright_enabled and is_taobao_product_url(url):
            browser_options: dict[str, object] = {
                "resolver": resolver,
                "timeout_ms": playwright_timeout_ms,
            }
            if taobao_state_path is not None:
                browser_options["state_path"] = taobao_state_path
            return await _extract_taobao_page(url, **browser_options)
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
