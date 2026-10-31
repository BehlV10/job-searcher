"""
Main Job Scraper and Aggregator Pipeline.
Coordinates scrapers across Greenhouse, Lever, LinkedIn, and Built In (Boston & NYC).
Deduplicates, parses, enriches with recruiter outreach intelligence,
and outputs data/jobs.json and web/jobs.json for GitHub Pages.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Any

from scraper.greenhouse_scraper import scrape_greenhouse_all
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

    # Seniority counts
    senior_staff_count = sum(1 for j in jobs if j.get("seniority") == "Senior Staff")
    principal_count = sum(1 for j in jobs if j.get("seniority") == "Principal")
    staff_count = sum(1 for j in jobs if j.get("seniority") == "Staff")
    senior_count = sum(1 for j in jobs if j.get("seniority") in ["Senior", "Lead"])

    # Discipline counts
    ml_count = sum(1 for j in jobs if j.get("discipline") == "Machine Learning / AI")
    general_swe_count = sum(1 for j in jobs if j.get("discipline") != "Machine Learning / AI")

    # Source breakdown
    sources_summary = {}
    for j in jobs:
        src = j.get("source", "Other")
        sources_summary[src] = sources_summary.get(src, 0) + 1

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
            "sources": ["LinkedIn", "Greenhouse", "Lever", "Built In"],
            "source_breakdown": sources_summary
        },
        "user_profile": user_profile,
        "jobs": jobs
    }


def run_pipeline():
    """Runs full multi-source scraping, parsing, enrichment and export pipeline."""
    logger.info("Starting Job Searcher ingestion pipeline...")
    config = load_config()
    user_info = config.get("user", {})

    collected_jobs = []

    # 1. Scrape Greenhouse boards
    logger.info("--- [1/4] Scraping Direct Greenhouse ATS Boards ---")
    try:
        gh_jobs = scrape_greenhouse_all()
        logger.info(f"Greenhouse total collected: {len(gh_jobs)}")
        collected_jobs.extend(gh_jobs)
    except Exception as e:
        logger.error(f"Error in Greenhouse pipeline: {e}")

    # 2. Scrape Lever boards
    logger.info("--- [2/4] Scraping Direct Lever ATS Boards ---")
    try:
        lever_jobs = scrape_lever_all()
        logger.info(f"Lever total collected: {len(lever_jobs)}")
        collected_jobs.extend(lever_jobs)
    except Exception as e:
        logger.error(f"Error in Lever pipeline: {e}")

    # 3. Scrape Built In Boston & Built In NYC
    logger.info("--- [3/4] Scraping Built In Boston & Built In NYC ---")
    try:
        builtin_jobs = scrape_builtin_all()
        logger.info(f"Built In total collected: {len(builtin_jobs)}")
        collected_jobs.extend(builtin_jobs)
    except Exception as e:
        logger.error(f"Error in Built In pipeline: {e}")

    # 4. Scrape LinkedIn public guest jobs
    logger.info("--- [4/4] Scraping LinkedIn Public Jobs ---")
    try:
        li_jobs = scrape_linkedin_all()
        logger.info(f"LinkedIn total collected: {len(li_jobs)}")
        collected_jobs.extend(li_jobs)
    except Exception as e:
        logger.error(f"Error in LinkedIn pipeline: {e}")

    # Deduplicate and rank
    processed_jobs = deduplicate_and_rank_jobs(collected_jobs)
    logger.info(f"Total unique jobs after deduplication: {len(processed_jobs)}")

    # Enrich
    final_payload = enrich_with_metadata(processed_jobs, user_info)

    # Save outputs
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

    print("\n================ PIPELINE SUMMARY ================")
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
    print("==================================================\n")

    return final_payload


if __name__ == "__main__":
    run_pipeline()
