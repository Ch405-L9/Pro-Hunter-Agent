# Changelog

All notable changes to Pro Hunter Agent are documented here.

---

## [1.1.0] - 2026-04-26

### Fixed (Critical)

- **`pipeline/runner.py`** — config read bug: `configs["providers"]` returns
  `{"providers": {...}}`, so `prov.get("llm", {})` always returned empty dict,
  defaulting to `qwen2.5:14b` on every run. Fixed with `.get("providers", prov)`.
  Root effect: all parse and score calls were silently using the 9GB model instead
  of configured `mistral:7b`, causing 300s timeouts on CPU.

- **`parsers/job_parser.py`** — parse snippet reduced from 6000 → 2000 chars.
  6000-char context on CPU with mistral:7b exceeds 300s timeout due to slow prefill.
  2000 chars gives sufficient title/company/location/description signal in ~78s.

- **`rag_bridge.py`** — ChromaDB rejects `None` metadata values. Added `or ""`
  fallback on all string fields; safe `join(field or [])` on tech_stack list.
  Previously caused `Cannot convert Python object to MetadataValue` on jobs where
  LLM returned null company_name (common on federal/USAJOBS postings).

- **`llm/client_ollama.py`** — generate timeout increased 120s → 300s.

### Changed

- **`config/providers.yaml`** — all LLM tasks (`model`, `scoring_model`, `parse_model`)
  switched from `qwen2.5:14b` to `mistral:7b`. System has 16GB RAM; 14b model (9GB)
  leaves insufficient headroom. mistral:7b (4.4GB) loads in ~6s, parses+scores in ~104s.

- **`config/skills.yaml`** — rebuilt from 8 generic profiles to 9 resume-grounded profiles:
  - **`ai-sw-engineer`** (PRIMARY) — matches actual role: AI Software Engineer & Developer
  - **`full-stack-dev`** — new, JavaScript/TypeScript/React/Node.js stack
  - **`workmarket-contractor`** — new, gig/contract $35/hr minimum
  - Updated `python-automation`, `ai-agents`, `devops-mlops`, `tech-support`,
    `field-support-engineer`, `federal-contracts` with real resume keywords

- **`config/sites.yaml`** — added 4 platforms:
  - `workmarket` — PRIMARY contractor platform, browseruse tier (auth required)
  - `ziprecruiter` — local/cloud tiers
  - `indeed_proton` — USER1 proton account
  - `indeed_gmail` — USER2 Gmail/Google-auth account with pre-filled remote tech search
  - Extended `remote_ok` and `dice` tiers to include `firecrawl_cloud`, `browseruse`

- **`config/identity.yaml`** — complete overhaul with full BADGRTechnologies LLC
  business data (EIN 33-3212015, DUNS 136411582, UEI U9GUGKVFGCA9, NAICS 541511),
  resume-derived skills/experience/certifications, and platform credentials.
  **File added to `.gitignore` — never committed.**

- **`.gitignore`** — added `config/identity.yaml` to prevent credential exposure.

### Verified (First Successful End-to-End Run)

Pipeline run confirmed working 2026-04-26 with mistral:7b:
- Scrape (local Playwright): 3s
- LLM parse (mistral:7b, 2000-char): ~78s — job title extracted correctly
- LLM score (mistral:7b): ~26s — fit notes returned ("does not align with python-automation profile")
- CSV save + RAG index: <1s
- **Total: ~107s end-to-end. No fallbacks.**

---

## [1.0.0] - 2026-04-26

### Added

**Core Package Structure**
- Created proper Python package layout: `scrapers/`, `parsers/`, `llm/`, `pipeline/`,
  `storage/`, `cli/`, `config/`, `tests/`
- Added `__init__.py` to all packages for correct module resolution

**Scrapers**
- `scrapers/base.py` — data models: `FetchResult`, `JobOpportunity`, `JobFitScore`, `ApplicationWorkflow`
- `scrapers/local_playwright.py` — headless Chromium scraper with captcha detection
- `scrapers/firecrawl_client.py` — Firecrawl self-hosted and cloud client
- `scrapers/browseruse_client.py` — LLM-driven browser automation (langchain-ollama)
- `scrapers/agenty_client.py` — Agenty async scraping with full polling loop
- `scrapers/strategy.py` — tiered fallback: local → firecrawl_self_hosted → firecrawl_cloud → browseruse → agenty

**Parsers**
- `parsers/job_parser.py` — LLM extraction with regex fallback; SHA-256 job IDs
- `parsers/form_parser.py` — LLM-based HTML form field detection

**LLM Layer**
- `llm/client_ollama.py` — async Ollama HTTP wrapper (generate + embed)
- `llm/client_cloud.py` — cloud fallback client
- `llm/scoring.py` — fit scoring against skill profiles via local Ollama
- `llm/resume_customizer.py` — cover letter and resume summary generation

**Pipeline**
- `pipeline/runner.py` — scrape → parse → score → save → RAG
- `pipeline/collector.py` — builds search URLs from config; `build_all_urls()`
- `pipeline/scheduler.py` — daily runner, cron-ready

**Storage**
- `storage/csv_io.py` — 50-field CRM CSV, dedup by job_id

**CLI**
- `cli/main.py` — `collect-score`, `apply`, `query`, `list`, `run-daily`

**Configuration**
- `config/sites.yaml` — 7 job sites
- `config/providers.yaml` — scraping tiers, LLM config, API quotas
- `config/skills.yaml` — 8 skill profiles
- `config/identity.yaml` — Brandon Anthony Grant / BADGRTechnologies LLC

**Integration**
- `rag_bridge.py` — indexes jobs into badgr_harness ChromaDB `job_opportunities`
- `mcp_server.py` — MCP stdio server: `job_search`, `job_query`, `job_apply`, `list_jobs`, `ingest_jobs_to_rag`
- `badgr_harness/.mcp.json` — registers pro-hunter MCP in Claude Code sessions

**Form Filling**
- `form_filler.py` — local Ollama via langchain-ollama; accepts identity dict

**Tests**
- `tests/test_core.py` — URL ID stability, CSV ops, collector, parser, scoring mock

### Fixed (v1.0.0 build)
- `browseruse_client.py` hardcoded `ChatOpenAI(gpt-4o)` → `ChatOllama`
- `form_filler.py` same GPT-4o hardcoding → Ollama
- `agenty_client.py` triggered async job but never polled → full polling loop added
- Flat file structure → proper package subdirectories with `__init__.py`
- `runner.py` relative config path → absolute path relative to `__file__`
- `csv_io.py` tech_stack separator `,` → `|`
