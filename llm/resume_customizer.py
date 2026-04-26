import json
import logging
from scrapers.base import JobOpportunity
from llm.client_ollama import OllamaClient

logger = logging.getLogger(__name__)


class ResumeCustomizer:
    def __init__(self, model: str = "qwen2.5:14b", base_url: str = "http://localhost:11434"):
        self.client = OllamaClient(model=model, base_url=base_url)

    async def customize(self, job: JobOpportunity, identity: dict) -> dict:
        personal = identity.get("personal", identity)
        name = personal.get("full_name", personal.get("name", "Candidate"))
        company = identity.get("business", {}).get("company_name", "")

        prompt = f"""Generate tailored application content for this job. Return ONLY valid JSON.

Candidate: {name} ({company})
Job: {job.job_title} at {job.company_name}
Location: {job.location_raw or "Remote"}
Description: {(job.description_snippet or "")[:1500]}

Return JSON with:
- cover_letter: 3-paragraph professional cover letter (plain text)
- resume_summary: 2-3 sentence professional summary tailored to this role
- key_skills_to_highlight: list of 5-7 skills to emphasize"""

        try:
            response = await self.client.generate(prompt, json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.warning("ResumeCustomizer error: %s", e)
            return {"cover_letter": "", "resume_summary": "", "key_skills_to_highlight": []}
