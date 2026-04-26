import asyncio
import logging
import httpx
from scrapers.base import FetchResult

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5   # seconds between polls
MAX_POLLS = 24      # max 2 minutes total wait


class AgentyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.agenty.com/v2"

    async def scrape(self, url: str) -> FetchResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Trigger async job
                resp = await client.post(
                    f"{self.base_url}/jobs/async",
                    json={"url": url},
                    params={"apikey": self.api_key},
                )
                if resp.status_code != 200:
                    return FetchResult(
                        status="failed", method_used="agenty", content="",
                        error=f"Trigger HTTP {resp.status_code}: {resp.text[:200]}"
                    )

                job_id = resp.json().get("job_id") or resp.json().get("id")
                if not job_id:
                    return FetchResult(
                        status="failed", method_used="agenty", content="",
                        error="No job_id in Agenty response"
                    )

                logger.info("Agenty job %s triggered for %s — polling...", job_id, url)

                # Poll for result
                for attempt in range(MAX_POLLS):
                    await asyncio.sleep(POLL_INTERVAL)
                    poll = await client.get(
                        f"{self.base_url}/jobs/{job_id}",
                        params={"apikey": self.api_key},
                    )
                    if poll.status_code != 200:
                        logger.warning("Poll attempt %d: HTTP %d", attempt + 1, poll.status_code)
                        continue

                    data = poll.json()
                    state = data.get("status", "").lower()

                    if state in ("completed", "done", "success"):
                        content = (
                            data.get("result", {}).get("markdown")
                            or data.get("result", {}).get("html")
                            or str(data.get("result", ""))
                        )
                        return FetchResult(status="ok", method_used="agenty", content=content)

                    if state in ("failed", "error"):
                        return FetchResult(
                            status="failed", method_used="agenty", content="",
                            error=f"Agenty job failed: {data.get('error', 'unknown')}"
                        )

                    logger.debug("Agenty poll %d/%d: state=%s", attempt + 1, MAX_POLLS, state)

                return FetchResult(
                    status="failed", method_used="agenty", content="",
                    error=f"Agenty job {job_id} timed out after {MAX_POLLS * POLL_INTERVAL}s"
                )

        except Exception as e:
            logger.warning("Agenty error for %s: %s", url, e)
            return FetchResult(status="failed", method_used="agenty", content="", error=str(e))
