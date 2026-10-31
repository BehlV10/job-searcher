"""
Greenhouse Job Board Scraper.
Fetches open engineering positions from top tech companies using Greenhouse.
Greenhouse provides complete job descriptions containing mandatory NYC/MA salary disclosures and YoE.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from scraper.parser import (
    clean_html,
    parse_salary,
    parse_yoe,
    parse_tech_stack,
    parse_seniority,
    parse_location_type
)
from scraper.recruiter_matcher import match_recruiter_for_job

logger = logging.getLogger(__name__)

# Expanded curated top tech companies hiring Senior/Staff SWEs in NYC & Boston
DEFAULT_GREENHOUSE_BOARDS = [
    {"name": "Toast", "token": "toast"},
    {"name": "Klaviyo", "token": "klaviyo"},
    {"name": "Datadog", "token": "datadog"},
    {"name": "MongoDB", "token": "mongodb"},
    {"name": "Braze", "token": "braze"},
    {"name": "Oscar Health", "token": "oscar"},
    {"name": "CarGurus", "token": "cargurus"},
    {"name": "Formlabs", "token": "formlabs"},
    {"name": "Starburst Data", "token": "starburst"},
    {"name": "Betterment", "token": "betterment"},
    {"name": "Squarespace", "token": "squarespace"},
    {"name": "Flatiron Health", "token": "flatironhealth"},
    {"name": "Cockroach Labs", "token": "cockroachlabs"}
]


def fetch_greenhouse_board(board_token: str, company_name: str, target_locations: List[str] = None) -> List[Dict[str, Any]]:
    """Fetches jobs from a single Greenhouse board token."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code != 200:
            logger.warning(f"Greenhouse [{company_name}] returned status {res.status_code}")
            return []

        data = res.json()
        raw_jobs = data.get("jobs", [])
        results = []

        for item in raw_jobs:
            title = item.get("title", "").strip()
            loc_obj = item.get("location", {})
            location_str = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)

            # Check if this role is in target locations (NYC, Boston, Remote)
            loc_info = parse_location_type(location_str, item.get("content", ""))
            city = loc_info["city"]

            # Filter for NYC, Boston, or Remote
            if city not in ["New York, NY", "Boston, MA", "Remote"]:
                loc_lower = location_str.lower()
                if "new york" in loc_lower or "nyc" in loc_lower or "manhattan" in loc_lower:
                    city = "New York, NY"
                elif "boston" in loc_lower or "cambridge" in loc_lower or "massachusetts" in loc_lower or "somerville" in loc_lower:
                    city = "Boston, MA"
                else:
                    continue

            # Check if title matches Senior/Staff/Lead engineering roles
            title_lower = title.lower()
            engineering_keywords = ["software engineer", "backend", "full stack", "frontend", "infrastructure", "systems engineer", "platform", "data engineer", "machine learning"]
            seniority_keywords = ["senior", "staff", "lead", "principal", "distinguished", "architect", "manager", "head", "director", "sr."]

            is_swe = any(k in title_lower for k in engineering_keywords)
            is_senior = any(k in title_lower for k in seniority_keywords)

            if not (is_swe and is_senior):
                continue

            raw_content = item.get("content", "")
            clean_desc = clean_html(raw_content)

            salary_info = parse_salary(clean_desc)
            yoe_info = parse_yoe(clean_desc)
            tech_stack = parse_tech_stack(clean_desc)
            seniority = parse_seniority(title)
            recruiter_info = match_recruiter_for_job(company_name, city, title)

            # Greenhouse updated_at date
            updated_at = item.get("updated_at", "")
            date_posted = updated_at[:10] if updated_at else "Recently"

            job_id = f"gh_{board_token}_{item.get('id')}"

            # Short snippet
            snippet = clean_desc[:260] + "..." if len(clean_desc) > 260 else clean_desc

            results.append({
                "id": job_id,
                "title": title,
                "company": company_name,
                "location": location_str,
                "city": city,
                "work_model": loc_info["work_model"],
                "seniority": seniority,
                "source": "Greenhouse",
                "apply_url": item.get("absolute_url", ""),
                "date_posted": date_posted,
                "salary": salary_info,
                "experience": yoe_info,
                "tech_stack": tech_stack,
                "snippet": snippet,
                "description": clean_desc,
                "recruiter": recruiter_info
            })

        logger.info(f"Greenhouse [{company_name}]: Extracted {len(results)} matching Senior/Staff jobs.")
        return results

    except Exception as e:
        logger.error(f"Error fetching Greenhouse for {company_name}: {e}")
        return []


def scrape_greenhouse_all(boards: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    """Scrapes all configured Greenhouse companies."""
    targets = boards or DEFAULT_GREENHOUSE_BOARDS
    all_jobs = []
    for b in targets:
        time.sleep(0.3)
        jobs = fetch_greenhouse_board(b["token"], b["name"])
        all_jobs.extend(jobs)
    return all_jobs
