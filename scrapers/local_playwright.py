import asyncio
import logging
from playwright.async_api import async_playwright
from scrapers.base import FetchResult

logger = logging.getLogger(__name__)


class LocalPlaywrightScraper:
    async def scrape(self, url: str, site_config: dict) -> FetchResult:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/119.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                if not response or response.status >= 400:
                    status_code = response.status if response else "No Response"
                    return FetchResult(
                        status="failed", method_used="local", content="",
                        error=f"HTTP {status_code}"
                    )

                content = await page.content()
                content_lower = content.lower()
                if "captcha" in content_lower or ("robot" in content_lower and len(content) < 5000):
                    return FetchResult(
                        status="failed", method_used="local", content="",
                        error="Captcha/bot-check detected"
                    )

                return FetchResult(status="ok", method_used="local", content=content)
            except Exception as e:
                logger.warning("Playwright error for %s: %s", url, e)
                return FetchResult(status="failed", method_used="local", content="", error=str(e))
            finally:
                await browser.close()
