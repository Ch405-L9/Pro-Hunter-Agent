"""
Scheduler — cron-ready daily/weekly job run logic.
Wire to cron: 0 8 * * * cd /home/t0n34781/projects/pro_hunter && python -m cli.main run-daily
"""
import asyncio
import logging
from pathlib import Path
from pipeline.runner import JobOpsPipeline
from pipeline.collector import JobCollector

logger = logging.getLogger(__name__)


async def run_daily(profile_keys: list = None, config_dir: Path = None):
    pipeline = JobOpsPipeline(config_dir=config_dir)
    collector = JobCollector(pipeline.configs["sites"], pipeline.configs["skills"])

    profiles = profile_keys or list(pipeline.configs["skills"]["skill_profiles"].keys())
    all_tasks = []

    for profile_key in profiles:
        urls_with_sites = collector.build_all_urls(profile_key)
        logger.info("Profile '%s': %d search URLs", profile_key, len(urls_with_sites))
        for url, site_key in urls_with_sites:
            all_tasks.append((url, site_key, profile_key))

    logger.info("Scheduler: %d total collection tasks", len(all_tasks))

    for url, site_key, profile_key in all_tasks:
        try:
            await pipeline.run_for_url(url, site_key, profile_key)
        except Exception as e:
            logger.error("Task failed url=%s profile=%s: %s", url, profile_key, e)
        await asyncio.sleep(2)  # polite rate limiting

    logger.info("Daily run complete")


if __name__ == "__main__":
    asyncio.run(run_daily())
