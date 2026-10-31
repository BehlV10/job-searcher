"""
Ashby Job Board Scraper.
Fetches open engineering positions from top modern tech companies and AI unicorns using Ashby ATS
(Ramp, Cursor / Anysphere, Linear, Modal Labs, etc.).
"""

import time
import logging
import requests
from typing import List, Dict, Any, Optional

from scraper.parser import (
    clean_html,
    parse_salary,
    parse_yoe,
    parse_tech_stack,
    parse_seniority,
    parse_discipline,
    parse_location_type
)
from scraper.recruiter_matcher import match_recruiter_for_job

logger = logging.getLogger(__name__)

DEFAULT_ASHBY_BOARDS = [
    {"name": "Ramp", "slug": "ramp"},
    {"name": "Cursor (Anysphere)", "slug": "cursor"},
    {"name": "Linear", "slug": "linear"},
    {"name": "Modal Labs", "slug": "modal"}
]


def fetch_ashby_board(board_slug: str, company_name: str) -> List[Dict[str, Any]]:
    """Fetches jobs for an Ashby board slug."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return []

        data = res.json()
        raw_jobs = data.get("jobs", [])
        results = []

        for item in raw_jobs:
            title = item.get("title", "").strip()
            loc_str = item.get("location", "")
            secondary_locs = [s.get("location", "") for s in item.get("secondaryLocations", []) if isinstance(s, dict)]
            combined_loc = f"{loc_str} {' '.join(secondary_locs)}"

            loc_info = parse_location_type(combined_loc, item.get("descriptionPlain", ""))
            city = loc_info["city"]

            if city not in ["New York, NY", "Boston, MA", "Remote"]:
                loc_lower = combined_loc.lower()
                if "new york" in loc_lower or "nyc" in loc_lower or "manhattan" in loc_lower:
                    city = "New York, NY"
                elif "boston" in loc_lower or "cambridge" in loc_lower or "massachusetts" in loc_lower:
                    city = "Boston, MA"
                else:
                    continue

            title_lower = title.lower()
            swe_terms = ["engineer", "backend", "full stack", "frontend", "infrastructure", "systems", "platform", "machine learning", "ai", "scientist"]
            senior_terms = ["senior", "staff", "lead", "principal", "architect", "manager", "head", "founding"]

            is_swe = any(k in title_lower for k in swe_terms)
            is_senior = any(k in title_lower for k in senior_terms)

            if not (is_swe and is_senior):
                continue

            desc_plain = item.get("descriptionPlain", "") or clean_html(item.get("descriptionHtml", ""))
            salary_info = parse_salary(desc_plain)
            yoe_info = parse_yoe(desc_plain)
            tech_stack = parse_tech_stack(desc_plain)
            seniority = parse_seniority(title)
            discipline = parse_discipline(title, desc_plain)
            recruiter_info = match_recruiter_for_job(company_name, city, title)

            published_at = item.get("publishedAt", "")
            date_posted = published_at[:10] if published_at else "Recently"

            work_model = "On-site"
            wp = item.get("workplaceType", "").lower()
            if "remote" in wp or item.get("isRemote"):
                work_model = "Remote"
            elif "hybrid" in wp:
                work_model = "Hybrid"

            snippet = desc_plain[:260] + "..." if len(desc_plain) > 260 else desc_plain
            job_id = f"ashby_{board_slug}_{item.get('id')}"

            results.append({
                "id": job_id,
                "title": title,
                "company": company_name,
                "location": loc_str or city,
                "city": city,
                "work_model": work_model,
                "seniority": seniority,
                "discipline": discipline,
                "source": "Ashby",
                "apply_url": item.get("jobUrl", item.get("applyUrl", "")),
                "date_posted": date_posted,
                "salary": salary_info,
                "experience": yoe_info,
                "tech_stack": tech_stack,
                "snippet": snippet,
                "description": desc_plain,
                "recruiter": recruiter_info
            })

        logger.info(f"Ashby [{company_name}]: Found {len(results)} matching positions.")
        return results

    except Exception as e:
        logger.error(f"Error fetching Ashby for {company_name}: {e}")
        return []


def scrape_ashby_all(boards: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    """Scrapes all configured Ashby boards."""
    targets = boards or DEFAULT_ASHBY_BOARDS
    all_jobs = []
    for b in targets:
        time.sleep(0.2)
        jobs = fetch_ashby_board(b["slug"], b["name"])
        all_jobs.extend(jobs)
    return all_jobs
