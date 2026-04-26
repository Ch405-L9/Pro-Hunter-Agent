"""
rag_bridge.py
Feeds scored job opportunities into the badgr_harness ChromaDB RAG.
Separate collection 'job_opportunities' — keeps job data isolated from badgr_corpus.
"""
import hashlib
import logging
import requests
from pathlib import Path
from scrapers.base import JobOpportunity, JobFitScore

logger = logging.getLogger(__name__)

BADGR_RAG_DB = Path("/home/t0n34781/projects/badgr_harness/rag_db")
COLLECTION = "job_opportunities"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


def _embed(text: str) -> list:
    r = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text[:2000]},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["embedding"]


def _get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(BADGR_RAG_DB))
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


async def push_job_to_rag(job: JobOpportunity, fit: JobFitScore = None):
    """
    Embeds job description + metadata into badgr_harness job_opportunities collection.
    Called automatically by runner after each successful scrape+score.
    """
    doc_text = _build_document(job, fit)
    doc_id = f"job_{job.job_id}"

    try:
        col = _get_collection()

        existing = col.get(ids=[doc_id])
        if existing["ids"]:
            logger.debug("Job %s already in RAG, updating", job.job_id)
            col.delete(ids=[doc_id])

        embedding = _embed(doc_text)
        metadata = {
            "job_id": job.job_id or "",
            "job_title": job.job_title or "",
            "company": job.company_name or "",
            "source_site": job.source_site or "",
            "location_type": job.location_type or "",
            "tech_stack": "|".join(job.tech_stack or []),
            "fit_score": str(fit.fit_score_overall) if fit else "0",
            "skill_profile": fit.skill_profile if fit else "",
        }

        col.add(ids=[doc_id], embeddings=[embedding], documents=[doc_text], metadatas=[metadata])
        logger.info("RAG: indexed job %s (%s @ %s)", job.job_id, job.job_title, job.company_name)

    except Exception as e:
        logger.warning("RAG bridge error for job %s: %s", job.job_id, e)


def _build_document(job: JobOpportunity, fit: JobFitScore = None) -> str:
    parts = [
        f"Job Title: {job.job_title}",
        f"Company: {job.company_name}",
        f"Source: {job.source_site}",
        f"Location: {job.location_raw or 'Unknown'} ({job.location_type or 'unknown'})",
        f"Employment Type: {job.employment_type or 'unknown'}",
    ]
    if job.salary_raw:
        parts.append(f"Salary: {job.salary_raw}")
    if job.tech_stack:
        parts.append(f"Tech Stack: {', '.join(job.tech_stack)}")
    if job.description_snippet:
        parts.append(f"Description: {job.description_snippet}")
    if fit:
        parts.append(f"Fit Score: {fit.fit_score_overall}/100 ({fit.skill_profile})")
        parts.append(f"Fit Notes: {fit.fit_notes}")

    return "\n".join(parts)


def query_jobs(query: str, k: int = 5, min_score: float = None) -> list:
    """
    Semantic search over indexed job opportunities.
    Optionally filter by minimum fit_score.
    """
    try:
        col = _get_collection()
        if col.count() == 0:
            return []

        vec = _embed(query)
        results = col.query(query_embeddings=[vec], n_results=min(k, col.count()))

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = float(meta.get("fit_score", 0))
            if min_score and score < min_score:
                continue
            hits.append({"document": doc, "metadata": meta, "distance": round(dist, 4)})

        return hits

    except Exception as e:
        logger.error("RAG query error: %s", e)
        return []
