import logging
from typing import Optional
from scrapers.base import FetchResult

logger = logging.getLogger(__name__)


class ScrapingStrategy:
    def __init__(self, providers_config: dict):
        self.providers = providers_config

    async def fetch(self, url: str, site_config: dict) -> FetchResult:
        tiers = site_config.get("strategy_tiers", self.providers.get("strategy_order", ["local"]))

        last_result: Optional[FetchResult] = None
        for tier in tiers:
            logger.info("Trying tier '%s' for %s", tier, url)
            result = await self._call_tier(tier, url)
            if result.status == "ok":
                logger.info("Tier '%s' succeeded", tier)
                return result
            logger.warning("Tier '%s' failed: %s", tier, result.error)
            last_result = result

        return last_result or FetchResult(
            status="failed", method_used="none", content="", error="No tiers attempted"
        )

    async def _call_tier(self, tier: str, url: str) -> FetchResult:
        try:
            if tier == "local":
                from scrapers.local_playwright import LocalPlaywrightScraper
                return await LocalPlaywrightScraper().scrape(url, {})

            elif tier == "firecrawl_self_hosted":
                from scrapers.firecrawl_client import FirecrawlClient
                sh_url = self.providers.get("firecrawl", {}).get("self_hosted_url", "http://localhost:3002")
                return await FirecrawlClient(base_url=sh_url).scrape(url)

            elif tier == "firecrawl_cloud":
                from scrapers.firecrawl_client import FirecrawlClient
                api_key = self.providers.get("firecrawl", {}).get("api_key")
                return await FirecrawlClient(api_key=api_key, base_url="https://api.firecrawl.dev").scrape(url)

            elif tier == "browseruse":
                from scrapers.browseruse_client import BrowserUseClient
                llm_cfg = self.providers.get("llm", {})
                return await BrowserUseClient(
                    ollama_model=llm_cfg.get("browseruse_model", llm_cfg.get("model", "qwen2.5:14b")),
                    ollama_base_url=llm_cfg.get("base_url", "http://localhost:11434"),
                ).scrape(url)

            elif tier == "agenty":
                from scrapers.agenty_client import AgentyClient
                api_key = self.providers.get("agenty", {}).get("api_key")
                return await AgentyClient(api_key=api_key).scrape(url)

            else:
                return FetchResult(status="failed", method_used=tier, content="", error=f"Unknown tier: {tier}")

        except Exception as e:
            return FetchResult(status="failed", method_used=tier, content="", error=str(e))
