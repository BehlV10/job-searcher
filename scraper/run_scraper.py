"""
High-Scale Job Scraper and Aggregator Pipeline.
Coordinates concurrent scrapers across:
1. Greenhouse (Reddit, Stripe, Cloudflare, Anthropic, Datadog, Toast, Klaviyo, etc.)
2. Ashby (Ramp, Cursor / Anysphere, Linear, Modal Labs, etc.)
3. Lever (Palantir, Spotify, Postman)
4. Built In (Boston & NYC multi-category)
5. LinkedIn Public Searches (Google, Microsoft, Salesforce, AMD, Logitech, Verily, HubSpot, etc.)

Uses multi-threading for blazing fast execution.
Deduplicates, categorizes seniority (Senior, Staff, Senior Staff, Principal),
separates Machine Learning / AI from General SWE,
and exports data/jobs.json, web/jobs.json, and root jobs.json for GitHub Pages.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from scraper.greenhouse_scraper import scrape_greenhouse_all
from scraper.ashby_scraper import scrape_ashby_all
from scraper.lever_scraper import scrape_lever_all
from scraper.linkedin_scraper import scrape_linkedin_all
from scraper.builtin_scraper import scrape_builtin_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("job_pipeline")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "profile.json"
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"


def load_config() -> Dict[str, Any]:
    """Loads configuration and user search profile."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def deduplicate_and_rank_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates jobs based on normalized company name and title.
    Prefers records with parsed salary, direct ATS sources, and detailed descriptions.
    """
    seen = {}
    for job in jobs:
        comp = job.get("company", "").strip().lower()
        title = job.get("title", "").strip().lower()
        clean_title = title.replace("-", " ").replace("–", " ").replace("/", " ")
        clean_title = " ".join(clean_title.split())
        key = f"{comp}::{clean_title}"

        if key not in seen:
            seen[key] = job
        else:
            existing = seen[key]
            if job.get("salary") and not existing.get("salary"):
                seen[key] = job
            elif len(job.get("description", "")) > len(existing.get("description", "")):
                seen[key] = job

    deduped = list(seen.values())

    def sort_key(j):
        has_sal = 1 if j.get("salary") else 0
        date = j.get("date_posted", "")
        return (has_sal, date)

    deduped.sort(key=sort_key, reverse=True)
    return deduped


def enrich_with_metadata(jobs: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Wraps jobs array with search metadata and candidate profile info."""
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    total = len(jobs)
    with_salary = sum(1 for j in jobs if j.get("salary"))
    nyc_count = sum(1 for j in jobs if j.get("city") == "New York, NY")
    boston_count = sum(1 for j in jobs if j.get("city") == "Boston, MA")

    senior_staff_count = sum(1 for j in jobs if j.get("seniority") == "Senior Staff")
    principal_count = sum(1 for j in jobs if j.get("seniority") == "Principal")
    staff_count = sum(1 for j in jobs if j.get("seniority") == "Staff")
    senior_count = sum(1 for j in jobs if j.get("seniority") in ["Senior", "Lead"])

    ml_count = sum(1 for j in jobs if j.get("discipline") == "Machine Learning / AI")
    general_swe_count = sum(1 for j in jobs if j.get("discipline") != "Machine Learning / AI")

    sources_summary = {}
    archetypes_summary = {}
    for j in jobs:
        src = j.get("source", "Other")
        sources_summary[src] = sources_summary.get(src, 0) + 1
        arch = j.get("archetype", "General Software")
        archetypes_summary[arch] = archetypes_summary.get(arch, 0) + 1

    return {
        "metadata": {
            "last_updated": now_iso,
            "total_jobs": total,
            "with_salary_count": with_salary,
            "nyc_jobs": nyc_count,
            "boston_jobs": boston_count,
            "senior_staff_jobs": senior_staff_count,
            "principal_jobs": principal_count,
            "staff_jobs": staff_count,
            "senior_jobs": senior_count,
            "ml_jobs": ml_count,
            "general_swe_jobs": general_swe_count,
            "sources": ["LinkedIn", "Greenhouse", "Lever", "Ashby", "Built In"],
            "source_breakdown": sources_summary,
            "archetype_breakdown": archetypes_summary
        },
        "user_profile": user_profile,
        "jobs": jobs
    }


def run_pipeline():
    """Runs full high-scale concurrent scraping, parsing, enrichment and export pipeline."""
    logger.info("Starting High-Scale Job Searcher Pipeline...")
    config = load_config()
    user_info = config.get("user", {})

    collected_jobs = []

    tasks = {
        "Greenhouse": scrape_greenhouse_all,
        "Ashby": scrape_ashby_all,
        "Lever": scrape_lever_all,
        "BuiltIn": scrape_builtin_all,
        "LinkedIn": scrape_linkedin_all
    }

    # Execute scrapers concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_source = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                jobs = future.result()
                logger.info(f"[{source_name}] Completed. Retrieved {len(jobs)} jobs.")
                collected_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"[{source_name}] Failed with error: {e}")

    # Deduplicate and rank
    processed_jobs = deduplicate_and_rank_jobs(collected_jobs)
    logger.info(f"Total unique jobs after deduplication: {len(processed_jobs)}")

    final_payload = enrich_with_metadata(processed_jobs, user_info)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    data_file = DATA_DIR / "jobs.json"
    web_file = WEB_DIR / "jobs.json"
    root_file = BASE_DIR / "jobs.json"

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)
    with open(web_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)
    with open(root_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)

    print("\n================ HIGH-SCALE PIPELINE SUMMARY ================")
    print(f"Total Active Listings: {len(processed_jobs)}")
    print(f"With Parsed Salary:   {final_payload['metadata']['with_salary_count']}")
    print(f"New York, NY:         {final_payload['metadata']['nyc_jobs']}")
    print(f"Boston, MA:           {final_payload['metadata']['boston_jobs']}")
    print(f"Senior Staff:         {final_payload['metadata']['senior_staff_jobs']}")
    print(f"Principal:            {final_payload['metadata']['principal_jobs']}")
    print(f"Staff:                {final_payload['metadata']['staff_jobs']}")
    print(f"Senior / Lead:        {final_payload['metadata']['senior_jobs']}")
    print(f"Machine Learning / AI:{final_payload['metadata']['ml_jobs']}")
    print(f"General SWE:          {final_payload['metadata']['general_swe_jobs']}")
    print("Source Breakdown:    ", final_payload['metadata']['source_breakdown'])
    print("=============================================================\n")

    return final_payload


if __name__ == "__main__":
    run_pipeline()
