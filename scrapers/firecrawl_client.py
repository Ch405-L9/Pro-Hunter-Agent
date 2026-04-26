import logging
import httpx
from scrapers.base import FetchResult

logger = logging.getLogger(__name__)


class FirecrawlClient:
    def __init__(self, api_key: str = None, base_url: str = "http://localhost:3002"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def scrape(self, url: str) -> FetchResult:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/scrape",
                    json={"url": url, "formats": ["markdown", "html"]},
                    headers=headers,
                    timeout=60.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    content = (
                        data.get("data", {}).get("markdown")
                        or data.get("data", {}).get("html")
                        or ""
                    )
                    method = "firecrawl_cloud" if "firecrawl.dev" in self.base_url else "firecrawl_self_hosted"
                    return FetchResult(status="ok", method_used=method, content=content)
                return FetchResult(
                    status="failed", method_used="firecrawl", content="",
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            logger.warning("Firecrawl error for %s: %s", url, e)
            return FetchResult(status="failed", method_used="firecrawl", content="", error=str(e))
