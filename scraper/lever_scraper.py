"""
Lever Job Board Scraper.
Fetches open engineering positions from top tech companies using Lever ATS (Palantir, Spotify, etc.).
"""

import time
import logging
import datetime
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

DEFAULT_LEVER_COMPANIES = [
    {"name": "Palantir", "slug": "palantir"},
    {"name": "Spotify", "slug": "spotify"},
    {"name": "Postman", "slug": "postman"}
]


def fetch_lever_company(slug: str, company_name: str) -> List[Dict[str, Any]]:
    """Fetches jobs for a company from Lever's public postings API."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return []

        raw_jobs = res.json()
        if not isinstance(raw_jobs, list):
            return []

        results = []
        for item in raw_jobs:
            title = item.get("text", "").strip()
            cats = item.get("categories", {}) or {}
            location_str = cats.get("location", "")
            all_locs = cats.get("allLocations", [])

            combined_loc = f"{location_str} {' '.join(all_locs)}"
            loc_info = parse_location_type(combined_loc)
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
            swe_terms = ["software", "backend", "full stack", "frontend", "infrastructure", "systems", "platform", "machine learning", "data engineer", "ai engineer"]
            senior_terms = ["senior", "staff", "lead", "principal", "architect", "manager", "head"]

            is_swe = any(k in title_lower for k in swe_terms)
            is_senior = any(k in title_lower for k in senior_terms)
            if not (is_swe and is_senior):
                continue

            desc_plain = item.get("descriptionPlain", "")
            add_plain = item.get("additionalPlain", "")
            full_text = f"{desc_plain}\n{add_plain}"

            salary_info = parse_salary(full_text)
            yoe_info = parse_yoe(full_text)
            tech_stack = parse_tech_stack(full_text)
            seniority = parse_seniority(title)
            discipline = parse_discipline(title, full_text)
            recruiter_info = match_recruiter_for_job(company_name, city, title)

            created_at_ms = item.get("createdAt")
            if created_at_ms:
                date_posted = datetime.datetime.fromtimestamp(created_at_ms / 1000.0).strftime("%Y-%m-%d")
            else:
                date_posted = "Recently"

            work_model = "On-site"
            workplace_type = item.get("workplaceType", "").lower()
            if "remote" in workplace_type:
                work_model = "Remote"
            elif "hybrid" in workplace_type:
                work_model = "Hybrid"

            snippet = desc_plain[:260] + "..." if len(desc_plain) > 260 else desc_plain

            results.append({
                "id": f"lever_{slug}_{item.get('id')}",
                "title": title,
                "company": company_name,
                "location": location_str or city,
                "city": city,
                "work_model": work_model,
                "seniority": seniority,
                "discipline": discipline,
                "source": "Lever",
                "apply_url": item.get("hostedUrl", item.get("applyUrl", "")),
                "date_posted": date_posted,
                "salary": salary_info,
                "experience": yoe_info,
                "tech_stack": tech_stack,
                "snippet": snippet,
                "description": full_text,
                "recruiter": recruiter_info
            })

        logger.info(f"Lever [{company_name}]: Found {len(results)} matching jobs.")
        return results

    except Exception as e:
        logger.error(f"Error fetching Lever for {company_name}: {e}")
        return []


def scrape_lever_all(companies: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    """Scrapes all configured Lever companies."""
    targets = companies or DEFAULT_LEVER_COMPANIES
    all_jobs = []
    for comp in targets:
        time.sleep(0.3)
        jobs = fetch_lever_company(comp["slug"], comp["name"])
        all_jobs.extend(jobs)
    return all_jobs
