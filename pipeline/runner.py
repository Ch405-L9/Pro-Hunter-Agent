import yaml
import asyncio
import logging
from pathlib import Path
from scrapers.strategy import ScrapingStrategy
from parsers.job_parser import JobParser
from llm.scoring import LLMScorer
from storage.csv_io import CSVStorage

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class JobOpsPipeline:
    def __init__(self, config_dir: Path = None):
        cfg_dir = Path(config_dir) if config_dir else _CONFIG_DIR
        self.configs = self._load_configs(cfg_dir)
        prov = self.configs["providers"].get("providers", self.configs["providers"])
        llm_cfg = prov.get("llm", {})

        self.strategy = ScrapingStrategy(prov)
        self.scorer = LLMScorer(
            model=llm_cfg.get("model", "qwen2.5:14b"),
            base_url=llm_cfg.get("base_url", "http://localhost:11434"),
        )
        self.parser = JobParser(llm_client=self.scorer)

        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        self.storage = CSVStorage(str(data_dir / "jobs.csv"))

    def _load_configs(self, cfg_dir: Path) -> dict:
        configs = {}
        for name in ["sites", "providers", "skills", "identity"]:
            path = cfg_dir / f"{name}.yaml"
            with open(path, "r") as f:
                configs[name] = yaml.safe_load(f)
        return configs

    async def run_for_url(self, url: str, site_key: str, skill_profile_key: str):
        logger.info("Processing %s", url)

        fetch_result = await self.strategy.fetch(
            url, self.configs["sites"].get("sites", {}).get(site_key, {})
        )
        if fetch_result.status != "ok":
            logger.error("Fetch failed for %s: %s", url, fetch_result.error)
            return None

        job = await self.parser.parse(fetch_result, site_key, url)
        job.scrape_method = fetch_result.method_used

        skill_profile = self.configs["skills"]["skill_profiles"].get(skill_profile_key)
        if not skill_profile:
            logger.error("Skill profile '%s' not found", skill_profile_key)
            return None

        fit_score = await self.scorer.score_job(job, skill_profile)
        self.storage.save_job(job, fit_score)
        logger.info("Saved: %s @ %s | score=%s", job.job_title, job.company_name, fit_score.fit_score_overall)

        # Push to RAG bridge (non-blocking)
        try:
            from rag_bridge import push_job_to_rag
            await push_job_to_rag(job, fit_score)
        except Exception as e:
            logger.debug("RAG bridge skip: %s", e)

        return job, fit_score

    async def run_batch(self, urls_with_sites: list, skill_profile_key: str):
        tasks = [self.run_for_url(url, site, skill_profile_key) for url, site in urls_with_sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r and not isinstance(r, Exception)]
