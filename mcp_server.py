"""
mcp_server.py
MCP server exposing pro_hunter capabilities as tools to badgr_harness and Claude.
Run: python mcp_server.py

Tools exposed:
- job_search: scrape + score a single job URL
- job_query: semantic search over indexed job opportunities
- job_apply: browser-based form fill (dry-run by default)
- ingest_jobs_to_rag: push all CSV jobs into badgr_harness RAG
- list_jobs: list top-N jobs from CRM by score
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("pro_hunter_mcp")

# Ensure pro_hunter package importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.runner import JobOpsPipeline
from storage.csv_io import CSVStorage
from rag_bridge import query_jobs, push_job_to_rag

_pipeline: JobOpsPipeline = None


def get_pipeline() -> JobOpsPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = JobOpsPipeline()
    return _pipeline


# ── MCP Protocol (stdio JSON-RPC) ────────────────────────────────────────────

TOOLS = [
    {
        "name": "job_search",
        "description": "Scrape, parse, and score a job posting URL. Saves result to CRM and indexes in RAG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL of the job posting"},
                "site": {"type": "string", "description": "Site key from sites.yaml (e.g. 'linkedin', 'indeed')"},
                "profile": {"type": "string", "description": "Skill profile key from skills.yaml (e.g. 'ai-agents')"},
            },
            "required": ["url", "site", "profile"],
        },
    },
    {
        "name": "job_query",
        "description": "Semantic search over indexed job opportunities in the RAG database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "k": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                "min_score": {"type": "number", "description": "Minimum fit score filter (0-100)", "default": 0},
            },
            "required": ["query"],
        },
    },
    {
        "name": "job_apply",
        "description": "Browser-automated form fill for a job application. Always dry-run unless explicitly set.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Application form URL"},
                "dry_run": {"type": "boolean", "description": "If true, fill but do NOT submit (default: true)", "default": True},
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_jobs",
        "description": "List top jobs from CRM CSV sorted by fit score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of jobs to return (default 10)", "default": 10},
                "min_score": {"type": "number", "description": "Minimum fit_score_overall filter", "default": 0},
                "profile": {"type": "string", "description": "Filter by skill profile name"},
            },
        },
    },
    {
        "name": "ingest_jobs_to_rag",
        "description": "Push all jobs from the CRM CSV into the badgr_harness RAG job_opportunities collection.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


async def handle_tool(name: str, args: dict) -> dict:
    pipeline = get_pipeline()

    if name == "job_search":
        result = await pipeline.run_for_url(args["url"], args["site"], args["profile"])
        if not result:
            return {"error": "Scrape or score failed — check logs"}
        job, fit = result
        return {
            "job_title": job.job_title,
            "company": job.company_name,
            "url": job.job_url,
            "fit_score": fit.fit_score_overall,
            "fit_notes": fit.fit_notes,
            "scrape_method": job.scrape_method,
        }

    elif name == "job_query":
        hits = query_jobs(args["query"], k=args.get("k", 5), min_score=args.get("min_score"))
        return {"results": hits, "count": len(hits)}

    elif name == "job_apply":
        from form_filler import FormFiller
        filler = FormFiller()
        dry_run = args.get("dry_run", True)
        result = await filler.fill_application(args["url"], dry_run=dry_run)
        return {"status": "dry_run_complete" if dry_run else "submitted", "result": str(result)}

    elif name == "list_jobs":
        storage_path = Path(__file__).parent / "data" / "jobs.csv"
        storage = CSVStorage(str(storage_path))
        all_jobs = storage.read_all()
        limit = args.get("limit", 10)
        min_score = args.get("min_score", 0)
        profile_filter = args.get("profile")

        filtered = [
            j for j in all_jobs
            if float(j.get("fit_score_overall") or 0) >= min_score
            and (not profile_filter or profile_filter in j.get("skill_profile", ""))
        ]
        filtered.sort(key=lambda j: float(j.get("fit_score_overall") or 0), reverse=True)
        return {"jobs": filtered[:limit], "total_filtered": len(filtered)}

    elif name == "ingest_jobs_to_rag":
        storage_path = Path(__file__).parent / "data" / "jobs.csv"
        storage = CSVStorage(str(storage_path))
        all_jobs = storage.read_all()
        count = 0
        for row in all_jobs:
            from scrapers.base import JobOpportunity, JobFitScore
            job = JobOpportunity(
                job_id=row["job_id"], source_site=row["source_site"],
                job_title=row["job_title"], company_name=row["company_name"],
                job_url=row["job_url"], description_snippet=row.get("description_snippet"),
                location_raw=row.get("location_raw"), location_type=row.get("location_type"),
                tech_stack=[t for t in row.get("tech_stack", "").split("|") if t],
                scrape_method=row.get("scrape_method"),
            )
            fit = None
            if row.get("skill_profile"):
                fit = JobFitScore(
                    skill_profile=row["skill_profile"],
                    fit_score_overall=float(row.get("fit_score_overall") or 0),
                    fit_score_must_have=float(row.get("fit_score_must_have") or 0),
                    fit_score_nice_to_have=float(row.get("fit_score_nice_to_have") or 0),
                    fit_score_location=float(row.get("fit_score_location") or 0),
                    fit_notes=row.get("fit_notes", ""),
                )
            await push_job_to_rag(job, fit)
            count += 1
        return {"ingested": count}

    return {"error": f"Unknown tool: {name}"}


async def main():
    logger.info("Pro Hunter MCP server starting on stdio")
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            req = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pro-hunter", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            try:
                result = await handle_tool(tool_name, tool_args)
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }
            except Exception as e:
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
                }
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}

        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
