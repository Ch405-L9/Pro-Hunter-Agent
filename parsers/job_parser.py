import json
import re
import logging
from typing import Optional
from scrapers.base import JobOpportunity, FetchResult

logger = logging.getLogger(__name__)


class JobParser:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def parse(self, fetch_result: FetchResult, source_site: str, url: str) -> JobOpportunity:
        if self.llm_client:
            try:
                return await self._parse_with_llm(fetch_result.content, source_site, url)
            except Exception as e:
                logger.warning("LLM parse failed, falling back to basic: %s", e)
        return self._parse_basic(fetch_result.content, source_site, url)

    def _parse_basic(self, content: str, source_site: str, url: str) -> JobOpportunity:
        title_match = re.search(r"<title>(.*?)</title>", content, re.I | re.S)
        title = title_match.group(1).strip() if title_match else "Unknown Title"
        title = re.sub(r"\s+", " ", title)

        return JobOpportunity(
            job_id=self._url_to_id(url),
            source_site=source_site,
            job_title=title,
            company_name="Unknown Company",
            job_url=url,
            raw_content=content,
        )

    async def _parse_with_llm(self, content: str, source_site: str, url: str) -> JobOpportunity:
        # Feed up to 6000 chars — more context = better extraction
        snippet = content[:2000]
        prompt = f"""Extract job details from the content below. Return ONLY valid JSON.

Fields to extract:
- job_title (string)
- company_name (string)
- company_website (string or null)
- location_raw (string or null)
- location_type: one of "onsite", "hybrid", "remote", or null
- country (string or null)
- posted_date (string or null)
- employment_type (string or null, e.g. "full-time", "contract")
- salary_raw (string or null)
- salary_min (number or null)
- salary_max (number or null)
- salary_currency (string or null, e.g. "USD")
- salary_period (string or null, e.g. "year", "hour")
- tech_stack (array of strings)
- seniority (string or null, e.g. "senior", "mid", "junior")
- description_snippet (first 800 chars of job description)

Content:
{snippet}"""

        response = await self.llm_client.generate(prompt, json_mode=True)
        data = json.loads(response)

        return JobOpportunity(
            job_id=self._url_to_id(url),
            source_site=source_site,
            job_title=data.get("job_title", "Unknown"),
            company_name=data.get("company_name", "Unknown"),
            company_website=data.get("company_website"),
            job_url=url,
            location_raw=data.get("location_raw"),
            location_type=data.get("location_type"),
            country=data.get("country"),
            posted_date=data.get("posted_date"),
            employment_type=data.get("employment_type"),
            salary_raw=data.get("salary_raw"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            salary_currency=data.get("salary_currency"),
            salary_period=data.get("salary_period"),
            tech_stack=data.get("tech_stack", []),
            seniority=data.get("seniority"),
            description_snippet=data.get("description_snippet"),
            raw_content=content,
        )

    @staticmethod
    def _url_to_id(url: str) -> str:
        # Stable 16-char ID from URL
        import hashlib
        return hashlib.sha256(url.encode()).hexdigest()[:16]
