import asyncio
import logging
import sys
from typing import Optional

# On Windows, Playwright requires ProactorEventLoop
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from app.config import settings


logger = logging.getLogger("gemini_cdp.manager")


class CDPManager:
    """Manages Playwright connection via Chrome DevTools Protocol (CDP)."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def lock(self) -> asyncio.Lock:
        """Lock to synchronize concurrent interactions on the Gemini tab."""
        return self._lock

    async def connect(self) -> Browser:
        """Establishes connection to the Chrome instance on the remote debugging port."""
        if self._browser and self._browser.is_connected():
            return self._browser

        logger.info("Connecting to Chrome browser via CDP: %s", settings.CDP_URL)
        if not self._playwright:
            self._playwright = await async_playwright().start()

        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                settings.CDP_URL,
                timeout=10000,
            )
            logger.info("CDP connection to Chrome established successfully.")
            return self._browser
        except Exception as exc:
            logger.error("Failed to connect via CDP to %s: %s", settings.CDP_URL, exc)
            raise ConnectionError(
                f"Could not connect to Chrome at {settings.CDP_URL}. "
                "Ensure Chrome is running with --remote-debugging-port=9222."
            ) from exc

    async def get_or_create_gemini_page(self) -> Page:
        """Finds an existing open Gemini tab or creates a new one."""
        browser = await self.connect()

        # Check if we already hold a valid, open Gemini page reference
        if self._page and not self._page.is_closed():
            try:
                if "gemini.google.com" in self._page.url:
                    return self._page
            except Exception:
                pass

        # Search across all contexts and open tabs
        contexts: list[BrowserContext] = browser.contexts
        if not contexts:
            context = await browser.new_context()
            contexts = [context]

        for ctx in contexts:
            for page in ctx.pages:
                if "gemini.google.com" in page.url:
                    logger.info("Found existing Gemini tab: %s", page.url)
                    self._page = page
                    await self._page.bring_to_front()
                    return self._page

        # No Gemini tab found: open a new tab in the primary context
        target_context = contexts[0]
        logger.info("No Gemini tab found. Opening a new tab to %s", settings.GEMINI_URL)
        self._page = await target_context.new_page()
        await self._page.goto(
            settings.GEMINI_URL,
            wait_until="domcontentloaded",
            timeout=settings.PAGE_LOAD_TIMEOUT_MS,
        )
        return self._page

    async def check_status(self) -> dict:
        """Verifies CDP connectivity and active Gemini tab status."""
        try:
            browser = await self.connect()
            contexts = browser.contexts
            gemini_found = False
            page_title = None
            page_url = None

            for ctx in contexts:
                for page in ctx.pages:
                    if "gemini.google.com" in page.url:
                        gemini_found = True
                        page_title = await page.title()
                        page_url = page.url
                        break
                if gemini_found:
                    break

            return {
                "connected": True,
                "cdp_url": settings.CDP_URL,
                "gemini_tab_found": gemini_found,
                "page_title": page_title,
                "url": page_url,
                "details": "Chrome is connected and operational." if gemini_found else "Chrome is connected but no Gemini tab is open.",
            }
        except Exception as exc:
            return {
                "connected": False,
                "cdp_url": settings.CDP_URL,
                "gemini_tab_found": False,
                "page_title": None,
                "url": None,
                "details": str(exc),
            }

    async def close(self) -> None:
        """Releases Playwright and CDP resources."""
        logger.info("Closing CDP manager.")
        self._page = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


cdp_manager = CDPManager()

