# Changelog

All notable changes to Pro Hunter Agent are documented here.

## [1.0.0] - 2026-04-26

### Added

**Core Package Structure**
- Created proper Python package layout: `scrapers/`, `parsers/`, `llm/`, `pipeline/`, `storage/`, `cli/`, `config/`, `tests/`
- Added `__init__.py` to all packages for correct module resolution

**Scrapers**
- `scrapers/base.py` — data models: `FetchResult`, `JobOpportunity`, `JobFitScore`, `ApplicationWorkflow`
- `scrapers/local_playwright.py` — headless Chromium scraper with captcha detection
- `scrapers/firecrawl_client.py` — Firecrawl self-hosted and cloud client
- `scrapers/browseruse_client.py` — LLM-driven browser automation using local Ollama (qwen2.5:14b) via langchain-ollama
- `scrapers/agenty_client.py` — Agenty async scraping with full polling loop (2-min timeout, 5s interval)
- `scrapers/strategy.py` — tiered fallback orchestration: local → firecrawl_self_hosted → firecrawl_cloud → browseruse → agenty

**Parsers**
- `parsers/job_parser.py` — LLM-based extraction (6000-char context) with regex fallback; stable SHA-256 job IDs
- `parsers/form_parser.py` — LLM-based HTML form field detection and categorization

**LLM Layer**
- `llm/client_ollama.py` — async Ollama HTTP wrapper (generate + embed)
- `llm/client_cloud.py` — OpenAI/cloud fallback client
- `llm/scoring.py` — fit scoring against skill profiles using local Ollama
- `llm/resume_customizer.py` — tailored cover letter and resume summary generation

**Pipeline**
- `pipeline/runner.py` — full scrape → parse → score → save → RAG pipeline
- `pipeline/collector.py` — builds search URLs from skills + sites config; `build_all_urls()` for batch runs
- `pipeline/scheduler.py` — daily/weekly run orchestration with rate limiting; cron-ready

**Storage**
- `storage/csv_io.py` — 50-field CRM CSV with dedup by job_id, workflow update support

**CLI**
- `cli/main.py` — entry points: `collect-score`, `apply`, `query`, `list`, `run-daily`

**Configuration**
- `config/sites.yaml` — 7 job sites: LinkedIn, Indeed, Wellfound, Dice, SAM.gov, USAJobs, RemoteOK
- `config/providers.yaml` — tiered scraping strategy, LLM model config, API quotas
- `config/skills.yaml` — 8 skill profiles: python-automation, ai-systems, federal-contracts, web-dev, ai-agents, devops-mlops, content-tech, data-engineering
- `config/identity.yaml` — personal and business identity for form filling (Brandon Anthony Grant / BADGRTechnologies LLC / UEI U9GUGKVFGCA9)

**Integration**
- `rag_bridge.py` — indexes scored job opportunities into badgr_harness ChromaDB (`job_opportunities` collection)
- `mcp_server.py` — MCP stdio server exposing 5 tools: `job_search`, `job_query`, `job_apply`, `list_jobs`, `ingest_jobs_to_rag`
- `badgr_harness/.mcp.json` — registers `pro-hunter` MCP server for use in Claude Code sessions

**Form Filling**
- `form_filler.py` — migrated from GPT-4o to local Ollama (langchain-ollama); accepts identity dict from pipeline config

**Tests**
- `tests/test_core.py` — covers URL ID stability, CSV save/read/dedup, collector URL building, parser basic HTML, scoring mock

### Fixed
- `browseruse_client.py` was hardcoded to `ChatOpenAI(model="gpt-4o")` — replaced with `ChatOllama` using configurable local model
- `form_filler.py` same GPT-4o hardcoding — replaced with Ollama via langchain-ollama
- `agenty_client.py` triggered async job but never polled for result — full polling loop added
- All files were flat in `pro_hunter/` root; imports like `from scrapers.strategy import ...` failed — resolved by creating proper package subdirectories
- `runner.py` used relative `config/` path — changed to absolute path relative to `__file__`
- `csv_io.py` `tech_stack` separator changed from `,` to `|` to avoid CSV field conflicts
- `description_snippet` cap increased from 500 to 800 chars for better scoring accuracy
- `job_parser.py` context window increased from 4000 to 6000 chars

### Dependencies Added
- `langchain-ollama` — local LLM backend for BrowserUse and FormFiller
- `langchain-community` — LangChain community integrations
- `chromadb` — vector database for RAG bridge
- `pdfplumber` — PDF text extraction (inherited from badgr_harness pattern)
- `openai` — cloud LLM fallback client
