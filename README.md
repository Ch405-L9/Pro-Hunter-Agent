# Pro Hunter Agent

AI-assisted job search and application system for BADGRTechnologies LLC. Scrapes job opportunities from multiple sources, scores them against skill profiles using local LLMs, tracks applications in a structured CRM, and automates form filling. Integrates with the badgr_harness system via MCP and ChromaDB RAG.

---

## Requirements

- Python 3.10+
- Ollama running locally with `qwen2.5:14b` and `nomic-embed-text` pulled
- Playwright (installed via pip, browser via `playwright install chromium`)
- Docker (optional, for self-hosted Firecrawl)
- API keys for Firecrawl cloud and/or Agenty (optional, only for Tier 2/3 scraping)

---

## Installation

```bash
git clone https://github.com/Ch405-L9/Pro-Hunter-Agent.git
cd Pro-Hunter-Agent

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

---

## Configuration

All configuration lives in `config/`. Edit these before first run:

| File | Purpose |
|------|---------|
| `config/identity.yaml` | Your personal and business info for form filling (name, email, UEI, etc.) |
| `config/skills.yaml` | Skill profiles used for job scoring — 8 profiles included |
| `config/providers.yaml` | API keys for Firecrawl, Agenty; LLM model selection; scraping tier order |
| `config/sites.yaml` | Job boards and their scraping strategy per site |

Sensitive keys reference environment variables in `providers.yaml` using `${VAR_NAME}` syntax. Set them in your shell or a `.env` file.

---

## Usage

All commands run from the project root with the virtual environment active.

**Scrape, parse, and score a single job URL:**
```bash
python -m cli.main collect-score \
  --url "https://remoteok.com/remote-python-jobs" \
  --site remote_ok \
  --profile python-automation
```

**Run daily collection across all sites for selected profiles:**
```bash
python -m cli.main run-daily --profiles ai-agents,python-automation
```

**Semantic search over indexed jobs:**
```bash
python -m cli.main query "Python automation remote" --min-score 70
```

**List top jobs from CRM by fit score:**
```bash
python -m cli.main list --limit 20 --min-score 60
```

**Browser-fill a job application (dry run by default):**
```bash
python -m cli.main apply --url "https://example.com/apply/job-123"
```

Results are saved to `data/jobs.csv`. Open in any spreadsheet application or query via the CLI.

---

## Architecture

```
pro_hunter/
├── scrapers/           Scraping layer (tiered fallback strategy)
│   ├── base.py         Data models: FetchResult, JobOpportunity, JobFitScore
│   ├── strategy.py     Tier orchestration: local -> firecrawl -> browseruse -> agenty
│   ├── local_playwright.py   Headless Chromium, captcha detection
│   ├── firecrawl_client.py   Firecrawl self-hosted and cloud
│   ├── browseruse_client.py  LLM-driven browser (Ollama, local-first)
│   └── agenty_client.py      Agenty async scraper with polling
├── parsers/            LLM-based data extraction
│   ├── job_parser.py   Job field extraction with regex fallback
│   └── form_parser.py  HTML form field detection and mapping
├── llm/                Local model integration
│   ├── client_ollama.py  Async Ollama HTTP client (generate + embed)
│   ├── client_cloud.py   OpenAI/cloud fallback
│   ├── scoring.py        Fit scoring against skill profiles
│   └── resume_customizer.py  Cover letter and resume summary generation
├── pipeline/           Orchestration
│   ├── runner.py       End-to-end: scrape -> parse -> score -> save -> RAG
│   ├── collector.py    Builds search URLs from config; batch job discovery
│   └── scheduler.py    Daily/weekly run logic, cron-ready
├── storage/
│   └── csv_io.py       50-field CRM CSV: job metadata, scores, workflow tracking
├── cli/
│   └── main.py         CLI entry points: collect-score, apply, query, list, run-daily
├── config/             YAML configuration (sites, providers, skills, identity)
├── mcp_server.py       MCP stdio server for badgr_harness integration
├── rag_bridge.py       Indexes jobs into ChromaDB (job_opportunities collection)
├── form_filler.py      Browser-based form automation (local LLM via langchain-ollama)
└── data/               Output directory (jobs.csv auto-created)
```

---

## Scraping Tiers

| Tier | Method | When Used |
|------|--------|-----------|
| 0 — local | Playwright headless Chromium | Default first attempt |
| 1 — firecrawl_self_hosted | Self-hosted Firecrawl at localhost:3002 | After local failure |
| 2 — firecrawl_cloud | Firecrawl cloud API | After self-hosted failure |
| 3 — browseruse | LLM-driven browser (Ollama qwen2.5:14b) | For interactive/JS-heavy pages |
| 4 — agenty | Agenty cloud API (async + polling) | Last resort for stubborn sites |

Tier order is configurable per-site in `config/sites.yaml` and globally in `config/providers.yaml`.

---

## Skill Profiles

Eight profiles are included out of the box:

- `python-automation` — scripting, web scraping, API integration
- `ai-systems` — LLM deployment, AI infrastructure, MLOps
- `federal-contracts` — SAM.gov, government procurement, UEI/CAGE
- `web-dev` — React, TypeScript, Node.js, full-stack
- `ai-agents` — LangChain, CrewAI, RAG, multi-agent, vector DBs
- `devops-mlops` — Docker, CI/CD, model serving, Linux
- `content-tech` — AI content pipelines, social automation, technical writing
- `data-engineering` — ETL, SQL, Pandas, Airflow, analytics

Add or modify profiles in `config/skills.yaml`.

---

## Integration with badgr_harness

The `rag_bridge.py` module feeds scored job opportunities into the badgr_harness ChromaDB instance at `/home/t0n34781/projects/badgr_harness/rag_db/` under the `job_opportunities` collection. This gives the broader AI system semantic search access to all tracked jobs.

The `mcp_server.py` exposes five tools over the MCP stdio protocol. The badgr_harness `.mcp.json` file registers this server so it is available automatically in Claude Code sessions opened in that project.

MCP tools: `job_search`, `job_query`, `job_apply`, `list_jobs`, `ingest_jobs_to_rag`.

---

## Cron Setup

To run daily collection automatically:

```bash
# Add to crontab: crontab -e
0 8 * * * cd /home/t0n34781/projects/pro_hunter && .venv/bin/python -m cli.main run-daily >> logs/daily.log 2>&1
```

---

## License

Private — BADGRTechnologies LLC. All rights reserved.
