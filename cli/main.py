import argparse
import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def cmd_collect_score(args):
    from pipeline.runner import JobOpsPipeline
    pipeline = JobOpsPipeline()
    result = await pipeline.run_for_url(args.url, args.site, args.profile)
    if result:
        job, fit = result
        print(f"\n{'─'*60}")
        print(f"  Job    : {job.job_title} @ {job.company_name}")
        print(f"  Score  : {fit.fit_score_overall}/100 ({fit.skill_profile})")
        print(f"  Notes  : {fit.fit_notes}")
        print(f"  Method : {job.scrape_method}")
        print(f"{'─'*60}")
    else:
        print("Failed — check logs above", file=sys.stderr)
        sys.exit(1)


async def cmd_apply(args):
    from pipeline.runner import JobOpsPipeline
    from form_filler import FormFiller
    pipeline = JobOpsPipeline()
    filler = FormFiller(identity=pipeline.configs["identity"])
    await filler.fill_application(args.url, dry_run=not args.submit)


async def cmd_query(args):
    from rag_bridge import query_jobs
    hits = query_jobs(args.query, k=args.k, min_score=args.min_score)
    if not hits:
        print("No results. Run collect-score first or lower --min-score.")
        return
    for i, h in enumerate(hits, 1):
        meta = h["metadata"]
        print(f"\n[{i}] {meta.get('job_title','?')} @ {meta.get('company','?')} | score={meta.get('fit_score','?')} | dist={h['distance']}")
        print(f"     {h['document'][:200]}")


async def cmd_run_daily(args):
    from pipeline.scheduler import run_daily
    profiles = args.profiles.split(",") if args.profiles else None
    await run_daily(profile_keys=profiles)


async def cmd_list(args):
    from storage.csv_io import CSVStorage
    from pathlib import Path
    storage = CSVStorage(str(Path(__file__).parent.parent / "data" / "jobs.csv"))
    jobs = storage.read_all()
    min_score = args.min_score
    jobs = [j for j in jobs if float(j.get("fit_score_overall") or 0) >= min_score]
    jobs.sort(key=lambda j: float(j.get("fit_score_overall") or 0), reverse=True)
    jobs = jobs[:args.limit]
    if not jobs:
        print("No jobs found.")
        return
    print(f"\n{'Score':>5}  {'Profile':<18}  {'Title':<35}  {'Company'}")
    print("─" * 80)
    for j in jobs:
        print(f"{float(j.get('fit_score_overall',0)):>5.0f}  {j.get('skill_profile',''):<18}  {j.get('job_title','')[:35]:<35}  {j.get('company_name','')}")


def main():
    parser = argparse.ArgumentParser(description="Pro Hunter — AI Job Search CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # collect-score
    p = sub.add_parser("collect-score", help="Scrape, parse, and score a job URL")
    p.add_argument("--url", required=True)
    p.add_argument("--site", required=True, help="Site key from config/sites.yaml")
    p.add_argument("--profile", required=True, help="Skill profile key from config/skills.yaml")

    # apply
    p = sub.add_parser("apply", help="Browser-fill a job application form")
    p.add_argument("--url", required=True)
    p.add_argument("--submit", action="store_true", default=False, help="Actually submit (default: dry-run)")

    # query
    p = sub.add_parser("query", help="Semantic search over indexed jobs")
    p.add_argument("query", nargs="+")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--min-score", type=float, default=0, dest="min_score")

    # list
    p = sub.add_parser("list", help="List top jobs from CRM")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--min-score", type=float, default=0, dest="min_score")

    # run-daily
    p = sub.add_parser("run-daily", help="Run daily collection across all sites and profiles")
    p.add_argument("--profiles", default=None, help="Comma-separated profile keys (default: all)")

    args = parser.parse_args()
    cmd_map = {
        "collect-score": cmd_collect_score,
        "apply": cmd_apply,
        "query": lambda a: cmd_query(type("A", (), {"query": " ".join(a.query), "k": a.k, "min_score": a.min_score})()),
        "list": cmd_list,
        "run-daily": cmd_run_daily,
    }
    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
