import logging
from typing import Dict, List
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class JobCollector:
    def __init__(self, sites_config: Dict, skills_config: Dict):
        self.sites_config = sites_config
        self.skills_config = skills_config

    def build_search_urls(self, site_key: str, profile_key: str) -> List[str]:
        site = self.sites_config.get("sites", {}).get(site_key, {})
        template = site.get("search_url")
        if not template:
            logger.debug("No search_url for site '%s'", site_key)
            return []

        profile = self.skills_config.get("skill_profiles", {}).get(profile_key, {})
        keywords_raw = " OR ".join(profile.get("keywords", [])[:3])
        keywords = quote_plus(keywords_raw)
        location = quote_plus("Remote")

        try:
            url = template.format(keywords=keywords, location=location)
            return [url]
        except KeyError as e:
            logger.warning("URL template placeholder missing: %s", e)
            return []

    def get_all_sites(self) -> List[str]:
        return list(self.sites_config.get("sites", {}).keys())

    def build_all_urls(self, profile_key: str) -> List[tuple]:
        """Returns list of (url, site_key) for all sites that have a search_url."""
        results = []
        for site_key in self.get_all_sites():
            for url in self.build_search_urls(site_key, profile_key):
                results.append((url, site_key))
        return results
