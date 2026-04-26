import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import FetchResult, JobOpportunity, JobFitScore, ApplicationWorkflow
from parsers.job_parser import JobParser
from storage.csv_io import CSVStorage
from pipeline.collector import JobCollector


# ── Parser tests ──────────────────────────────────────────────────────────────

def test_url_to_id_stable():
    id1 = JobParser._url_to_id("https://example.com/job/123")
    id2 = JobParser._url_to_id("https://example.com/job/123")
    assert id1 == id2
    assert len(id1) == 16


@pytest.mark.asyncio
async def test_parse_basic_html():
    parser = JobParser()
    fetch = FetchResult(
        status="ok", method_used="local",
        content="<html><title>Senior Python Developer</title><body>Join TechCorp!</body></html>"
    )
    job = await parser.parse(fetch, "test_site", "https://test.com/job/1")
    assert job.job_title == "Senior Python Developer"
    assert job.source_site == "test_site"
    assert job.job_url == "https://test.com/job/1"


# ── Storage tests ─────────────────────────────────────────────────────────────

def test_csv_save_and_read(tmp_path):
    storage = CSVStorage(str(tmp_path / "jobs.csv"))
    job = JobOpportunity(
        job_id="test_001", source_site="linkedin",
        job_title="AI Engineer", company_name="TestCo",
        job_url="https://example.com/job/1",
        tech_stack=["Python", "LangChain"],
        description_snippet="Build AI agents",
    )
    fit = JobFitScore(
        skill_profile="ai-agents",
        fit_score_overall=88, fit_score_must_have=90,
        fit_score_nice_to_have=75, fit_score_location=100,
        fit_notes="Strong match on RAG and agents",
    )
    storage.save_job(job, fit)
    rows = storage.read_all()
    assert len(rows) == 1
    assert rows[0]["job_title"] == "AI Engineer"
    assert rows[0]["fit_score_overall"] == "88"
    assert rows[0]["tech_stack"] == "Python|LangChain"


def test_csv_update_existing(tmp_path):
    storage = CSVStorage(str(tmp_path / "jobs.csv"))
    job = JobOpportunity(
        job_id="dup_001", source_site="indeed",
        job_title="DevOps Engineer", company_name="Cloud Inc",
        job_url="https://example.com/job/2",
    )
    storage.save_job(job)
    job.job_title = "Senior DevOps Engineer"
    storage.save_job(job)
    rows = storage.read_all()
    assert len(rows) == 1
    assert rows[0]["job_title"] == "Senior DevOps Engineer"


# ── Collector tests ───────────────────────────────────────────────────────────

def test_collector_build_url():
    sites = {"sites": {"linkedin": {"search_url": "https://linkedin.com/jobs?q={keywords}&l={location}"}}}
    skills = {"skill_profiles": {"ai-agents": {"keywords": ["AI agents", "LangChain", "RAG"]}}}
    collector = JobCollector(sites, skills)
    urls = collector.build_search_urls("linkedin", "ai-agents")
    assert len(urls) == 1
    assert "linkedin.com" in urls[0]
    assert "AI" in urls[0] or "ai" in urls[0].lower()


def test_collector_missing_site():
    sites = {"sites": {}}
    skills = {"skill_profiles": {"ai-agents": {"keywords": ["AI"]}}}
    collector = JobCollector(sites, skills)
    urls = collector.build_search_urls("nonexistent", "ai-agents")
    assert urls == []


# ── Scoring mock test ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_mock():
    from llm.scoring import LLMScorer

    class MockScorer(LLMScorer):
        async def generate(self, prompt, json_mode=False):
            return '{"fit_score_overall": 85, "fit_score_must_have": 90, "fit_score_nice_to_have": 70, "fit_score_location": 100, "fit_notes": "Strong Python and automation match."}'

    scorer = MockScorer(model="test")
    job = JobOpportunity(
        job_id="score_001", source_site="test",
        job_title="Python Dev", company_name="Tech",
        job_url="https://test.com",
        description_snippet="Python automation expert",
    )
    profile = {"name": "python-automation", "must_have": ["Python"]}
    score = await scorer.score_job(job, profile)
    assert score.fit_score_overall == 85
    assert score.skill_profile == "python-automation"
