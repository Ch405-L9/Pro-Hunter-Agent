import json
import logging
from scrapers.base import JobOpportunity, JobFitScore
from llm.client_ollama import OllamaClient

logger = logging.getLogger(__name__)


class LLMScorer:
    def __init__(self, model: str = "qwen2.5:14b", base_url: str = "http://localhost:11434"):
        self.client = OllamaClient(model=model, base_url=base_url)

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        return await self.client.generate(prompt, json_mode=json_mode)

    async def score_job(self, job: JobOpportunity, skill_profile: dict) -> JobFitScore:
        description = job.description_snippet or job.raw_content or ""
        prompt = f"""Score this job opportunity against the skill profile below. Return ONLY valid JSON.

Skill Profile: {json.dumps(skill_profile)}

Job: {job.job_title} at {job.company_name}
Location: {job.location_raw or "Unknown"} ({job.location_type or "unknown"})
Tech Stack: {", ".join(job.tech_stack) if job.tech_stack else "not specified"}
Description: {description[:2000]}

Return JSON with these exact keys:
- fit_score_overall: integer 0-100
- fit_score_must_have: integer 0-100 (how many must-haves match)
- fit_score_nice_to_have: integer 0-100 (how many nice-to-haves match)
- fit_score_location: integer 0-100 (100=perfect location match, 0=deal-breaker)
- fit_notes: string, 1-2 sentences explaining the score"""

        try:
            response = await self.client.generate(prompt, json_mode=True)
            data = json.loads(response)
        except Exception as e:
            logger.warning("Scoring LLM error: %s", e)
            data = {}

        return JobFitScore(
            skill_profile=skill_profile.get("name", "unknown"),
            fit_score_overall=data.get("fit_score_overall", 0),
            fit_score_must_have=data.get("fit_score_must_have", 0),
            fit_score_nice_to_have=data.get("fit_score_nice_to_have", 0),
            fit_score_location=data.get("fit_score_location", 0),
            fit_notes=data.get("fit_notes", "Scoring unavailable"),
        )
