"""A small server-side Playwright session for manually completing Taobao login."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

try:
    from playwright.async_api import Browser, BrowserContext, Page
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - packaging installs Playwright in production
    Browser = object  # type: ignore[assignment,misc]
    BrowserContext = object  # type: ignore[assignment,misc]
    Page = object  # type: ignore[assignment,misc]
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None


TAOBAO_LOGIN_URL = "https://login.taobao.com/member/login.jhtml"
LoginAction = Literal["click", "type", "press", "drag", "reload"]


@dataclass
class _LoginSession:
    session_id: UUID
    browser: Browser
    context: BrowserContext
    page: Page


class TaobaoLoginManager:
    def __init__(self, state_path: Path, timeout_ms: int = 20_000) -> None:
        self.state_path = state_path
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._session: _LoginSession | None = None

    async def start(self) -> dict[str, object]:
        await self.close()
        if async_playwright is None:
            raise RuntimeError("Playwright 未安装")
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0 Safari/537.36 GiftMind/1.0"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()
        self._session = _LoginSession(uuid4(), browser, context, page)
        try:
            await page.goto(TAOBAO_LOGIN_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except Exception:
            await self.close()
            raise
        return await self.status(self._session.session_id)

    async def status(self, session_id: UUID) -> dict[str, object]:
        session = self._require(session_id)
        cookies = await session.context.cookies()
        current_url = session.page.url
        login_host = ("login.taobao.com", "passport.taobao.com", "login.tmall.com")
        host = current_url.split("/", 3)[2].split(":", 1)[0] if "://" in current_url else ""
        ready = bool(cookies) and not any(host == item or host.endswith(f".{item}") for item in login_host)
        return {
            "sessionId": str(session.session_id),
            "ready": ready,
            "url": current_url,
            "cookieCount": len(cookies),
            "stateSaved": self.state_path.is_file(),
        }

    async def screenshot(self, session_id: UUID) -> bytes:
        session = self._require(session_id)
        return await session.page.screenshot(type="png", animations="disabled")

    async def action(
        self,
        session_id: UUID,
        action: LoginAction,
        *,
        x: float | None = None,
        y: float | None = None,
        end_x: float | None = None,
        end_y: float | None = None,
        text: str | None = None,
        key: str | None = None,
    ) -> dict[str, object]:
        session = self._require(session_id)
        if action == "click":
            await session.page.mouse.click(self._coordinate(x), self._coordinate(y))
        elif action == "drag":
            if end_x is None or end_y is None:
                raise ValueError("拖动操作缺少终点坐标")
            await session.page.mouse.move(self._coordinate(x), self._coordinate(y))
            await session.page.mouse.down()
            await session.page.mouse.move(end_x, end_y, steps=12)
            await session.page.mouse.up()
        elif action == "type":
            if not text:
                raise ValueError("输入内容不能为空")
            await session.page.keyboard.type(text, delay=20)
        elif action == "press":
            if not key:
                raise ValueError("按键不能为空")
            await session.page.keyboard.press(key)
        elif action == "reload":
            await session.page.reload(wait_until="domcontentloaded", timeout=self.timeout_ms)
        else:
            raise ValueError("不支持的浏览器操作")
        try:
            await session.page.wait_for_load_state("domcontentloaded", timeout=1500)
        except PlaywrightTimeoutError:
            pass
        return await self.status(session_id)

    async def save(self, session_id: UUID) -> dict[str, object]:
        session = self._require(session_id)
        current = await self.status(session_id)
        if not current["ready"]:
            raise ValueError("淘宝登录尚未完成")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        await session.context.storage_state(path=str(self.state_path))
        try:
            self.state_path.chmod(0o600)
        except OSError:
            pass
        current["stateSaved"] = True
        return current

    async def clear(self) -> None:
        await self.close()
        if self.state_path.exists():
            self.state_path.unlink()

    def health(self) -> dict[str, object]:
        return {
            "browserAvailable": async_playwright is not None,
            "sessionActive": self._session is not None,
            "stateSaved": self.state_path.is_file(),
        }

    async def close(self) -> None:
        if self._session is not None:
            try:
                await self._session.context.close()
            finally:
                await self._session.browser.close()
        self._session = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    def _require(self, session_id: UUID) -> _LoginSession:
        if self._session is None or self._session.session_id != session_id:
            raise KeyError("淘宝登录会话不存在或已过期")
        return self._session

    @staticmethod
    def _coordinate(value: float | None) -> float:
        if value is None or value < 0 or value > 3000:
            raise ValueError("坐标无效")
        return value
