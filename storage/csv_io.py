import csv
import os
import logging
from typing import List, Dict, Any, Optional
from scrapers.base import JobOpportunity, JobFitScore, ApplicationWorkflow

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "job_id", "source_site", "job_title", "company_name", "company_website", "job_url",
    "location_raw", "location_type", "country", "posted_date", "scraped_date",
    "employment_type", "salary_raw", "salary_min", "salary_max", "salary_currency",
    "salary_period", "tech_stack", "seniority", "description_snippet",
    "skill_profile", "fit_score_overall", "fit_score_must_have", "fit_score_nice_to_have",
    "fit_score_location", "fit_notes",
    "status", "priority", "application_channel", "resume_version", "resume_customized",
    "cover_letter_sent", "application_submitted", "application_date",
    "recruiter_name", "recruiter_email", "recruiter_linkedin",
    "followup_1_due_date", "followup_1_done", "followup_1_notes",
    "followup_2_due_date", "followup_2_done", "followup_2_notes",
    "last_contact_date", "last_contact_type", "outcome", "scrape_method",
]


class CSVStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()

    def save_job(
        self,
        job: JobOpportunity,
        fit: Optional[JobFitScore] = None,
        workflow: Optional[ApplicationWorkflow] = None,
    ):
        data = self._serialize(job, fit, workflow)
        jobs = self.read_all()

        updated = False
        for i, existing in enumerate(jobs):
            if existing["job_id"] == job.job_id:
                jobs[i] = data
                updated = True
                break

        if not updated:
            jobs.append(data)

        with open(self.file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(jobs)

        logger.debug("Saved job %s (updated=%s)", job.job_id, updated)

    def read_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def update_workflow(self, job_id: str, workflow: ApplicationWorkflow):
        jobs = self.read_all()
        for job_row in jobs:
            if job_row["job_id"] == job_id:
                wf_data = self._serialize_workflow(workflow)
                job_row.update(wf_data)
                break
        with open(self.file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(jobs)

    def _serialize(
        self,
        job: JobOpportunity,
        fit: Optional[JobFitScore],
        workflow: Optional[ApplicationWorkflow],
    ) -> Dict[str, Any]:
        res = {
            "job_id": job.job_id,
            "source_site": job.source_site,
            "job_title": job.job_title,
            "company_name": job.company_name,
            "company_website": job.company_website or "",
            "job_url": job.job_url,
            "location_raw": job.location_raw or "",
            "location_type": job.location_type or "",
            "country": job.country or "",
            "posted_date": job.posted_date or "",
            "scraped_date": job.scraped_date,
            "employment_type": job.employment_type or "",
            "salary_raw": job.salary_raw or "",
            "salary_min": job.salary_min or "",
            "salary_max": job.salary_max or "",
            "salary_currency": job.salary_currency or "",
            "salary_period": job.salary_period or "",
            "tech_stack": "|".join(job.tech_stack),
            "seniority": job.seniority or "",
            "description_snippet": (job.description_snippet or "")[:800],
            "scrape_method": job.scrape_method or "",
        }

        if fit:
            res.update({
                "skill_profile": fit.skill_profile,
                "fit_score_overall": fit.fit_score_overall,
                "fit_score_must_have": fit.fit_score_must_have,
                "fit_score_nice_to_have": fit.fit_score_nice_to_have,
                "fit_score_location": fit.fit_score_location,
                "fit_notes": fit.fit_notes,
            })
        else:
            for field in ["skill_profile", "fit_score_overall", "fit_score_must_have",
                          "fit_score_nice_to_have", "fit_score_location", "fit_notes"]:
                res[field] = ""

        res.update(self._serialize_workflow(workflow or ApplicationWorkflow()))
        return res

    @staticmethod
    def _serialize_workflow(wf: ApplicationWorkflow) -> Dict[str, Any]:
        return {
            "status": wf.status,
            "priority": wf.priority,
            "application_channel": wf.application_channel or "",
            "resume_version": wf.resume_version or "",
            "resume_customized": "yes" if wf.resume_customized else "no",
            "cover_letter_sent": "yes" if wf.cover_letter_sent else "no",
            "application_submitted": "yes" if wf.application_submitted else "no",
            "application_date": wf.application_date or "",
            "recruiter_name": wf.recruiter_name or "",
            "recruiter_email": wf.recruiter_email or "",
            "recruiter_linkedin": wf.recruiter_linkedin or "",
            "followup_1_due_date": wf.followup_1_due_date or "",
            "followup_1_done": "yes" if wf.followup_1_done else "no",
            "followup_1_notes": wf.followup_1_notes or "",
            "followup_2_due_date": wf.followup_2_due_date or "",
            "followup_2_done": "yes" if wf.followup_2_done else "no",
            "followup_2_notes": wf.followup_2_notes or "",
            "last_contact_date": wf.last_contact_date or "",
            "last_contact_type": wf.last_contact_type or "",
            "outcome": wf.outcome or "",
        }
