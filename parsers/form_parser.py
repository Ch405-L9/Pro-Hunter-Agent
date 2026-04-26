import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FormParser:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def detect_fields(self, html_content: str) -> Dict[str, Any]:
        prompt = f"""Analyze this HTML form and identify all input fields.
Map each field name/id/label to a standard category from this list:
first_name, last_name, full_name, email, phone, address_street, address_city,
address_state, address_zip, country, linkedin_url, github_url, portfolio_url,
resume_upload, cover_letter_text, company_name, uei_number, cage_code,
years_experience, salary_expectation, start_date, other.

Return ONLY valid JSON: {{"field_id_or_name": "category", ...}}

HTML (first 5000 chars):
{html_content[:5000]}"""

        try:
            response = await self.llm_client.generate(prompt, json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.warning("FormParser LLM error: %s", e)
            return {}
