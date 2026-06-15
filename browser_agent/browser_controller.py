"""
browser_agent/browser_controller.py
===================================
Singleton controller for managing Playwright instances.
Ensures we reuse a single browser window across tasks, saving resources.
"""

import logging
from playwright.sync_api import sync_playwright, Playwright, Browser, Page, BrowserContext
from config import BROWSER_HEADLESS, BROWSER_TYPE, BROWSER_TIMEOUT_MS

logger = logging.getLogger("msa.browser.controller")


class BrowserController:
    """
    Singleton managing a single Playwright browser instance.
    Supports lazy initialization and proper cleanup.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BrowserController, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self._initialized = True

    def launch(self) -> Page:
        """Lazily starts playwright and browser if not already running."""
        if self.page and not self.page.is_closed():
            return self.page

        try:
            logger.info("Starting Playwright (headless=%s, type=%s)...", BROWSER_HEADLESS, BROWSER_TYPE)
            self.playwright = sync_playwright().start()

            # Select browser type
            if BROWSER_TYPE == "firefox":
                launcher = self.playwright.firefox
            elif BROWSER_TYPE == "webkit":
                launcher = self.playwright.webkit
            else:
                launcher = self.playwright.chromium

            self.browser = launcher.launch(headless=BROWSER_HEADLESS)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.context.set_default_timeout(BROWSER_TIMEOUT_MS)
            self.page = self.context.new_page()
            logger.info("Playwright browser launched and new page created.")
            return self.page
        except Exception as e:
            logger.exception("Failed to launch Playwright browser")
            self.close()
            raise e

    def close(self) -> None:
        """Close page, context, browser, and stop playwright."""
        logger.info("Closing Playwright browser...")
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
                self.page = None

            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
                self.context = None

            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
                self.browser = None

            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None
            logger.info("Playwright browser closed.")
        except Exception as e:
            logger.error("Error closing Playwright browser: %s", e)

    def get_page(self) -> Page:
        """Get the active page or launch a new one."""
        return self.launch()


# Singleton instance
controller = BrowserController()
