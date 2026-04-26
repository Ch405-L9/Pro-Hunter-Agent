from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class FetchResult:
    status: str  # "ok" or "failed"
    method_used: str
    content: str
    error: Optional[str] = None


@dataclass
class JobOpportunity:
    job_id: str
    source_site: str
    job_title: str
    company_name: str
    job_url: str
    company_website: Optional[str] = None
    location_raw: Optional[str] = None
    location_type: Optional[str] = None
    country: Optional[str] = None
    posted_date: Optional[str] = None
    scraped_date: str = field(default_factory=lambda: datetime.now().isoformat())
    employment_type: Optional[str] = None
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    seniority: Optional[str] = None
    description_snippet: Optional[str] = None
    raw_content: Optional[str] = None
    scrape_method: Optional[str] = None


@dataclass
class JobFitScore:
    skill_profile: str
    fit_score_overall: float
    fit_score_must_have: float
    fit_score_nice_to_have: float
    fit_score_location: float
    fit_notes: str


@dataclass
class ApplicationWorkflow:
    status: str = "backlog"
    priority: int = 3
    application_channel: Optional[str] = None
    resume_version: Optional[str] = None
    resume_customized: bool = False
    cover_letter_sent: bool = False
    application_submitted: bool = False
    application_date: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    followup_1_due_date: Optional[str] = None
    followup_1_done: bool = False
    followup_1_notes: Optional[str] = None
    followup_2_due_date: Optional[str] = None
    followup_2_done: bool = False
    followup_2_notes: Optional[str] = None
    last_contact_date: Optional[str] = None
    last_contact_type: Optional[str] = None
    outcome: Optional[str] = None
