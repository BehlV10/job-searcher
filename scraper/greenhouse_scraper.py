"""
Greenhouse Job Board Scraper.
Fetches open engineering positions from top tech companies and unicorns using Greenhouse
(Reddit, Stripe, Cloudflare, Anthropic, Airbnb, Pinterest, Coinbase, Datadog, Toast, Klaviyo, etc.).
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
    parse_discipline,
    parse_job_archetype,
    parse_exact_date,
    parse_location_type
)
from scraper.recruiter_matcher import match_recruiter_for_job

logger = logging.getLogger(__name__)

# Curated top 45+ tech giants, unicorns & employers on Greenhouse
DEFAULT_GREENHOUSE_BOARDS = [
    {"name": "Reddit", "token": "reddit"},
    {"name": "Stripe", "token": "stripe"},
    {"name": "Databricks", "token": "databricks"},
    {"name": "Cloudflare", "token": "cloudflare"},
    {"name": "Anthropic", "token": "anthropic"},
    {"name": "Datadog", "token": "datadog"},
    {"name": "Toast", "token": "toast"},
    {"name": "Klaviyo", "token": "klaviyo"},
    {"name": "MongoDB", "token": "mongodb"},
    {"name": "Airbnb", "token": "airbnb"},
    {"name": "Pinterest", "token": "pinterest"},
    {"name": "Coinbase", "token": "coinbase"},
    {"name": "Affirm", "token": "affirm"},
    {"name": "Roblox", "token": "roblox"},
    {"name": "Scale AI", "token": "scaleai"},
    {"name": "Waymo", "token": "waymo"},
    {"name": "Robinhood", "token": "robinhood"},
    {"name": "Flexport", "token": "flexport"},
    {"name": "Instacart", "token": "instacart"},
    {"name": "Gusto", "token": "gusto"},
    {"name": "Checkr", "token": "checkr"},
    {"name": "Chime", "token": "chime"},
    {"name": "SeatGeek", "token": "seatgeek"},
    {"name": "Fivetran", "token": "fivetran"},
    {"name": "Zocdoc", "token": "zocdoc"},
    {"name": "Carta", "token": "carta"},
    {"name": "Harry's", "token": "harrys"},
    {"name": "Markforged", "token": "markforged"},
    {"name": "Yext", "token": "yext"},
    {"name": "Twitch", "token": "twitch"},
    {"name": "Lyft", "token": "lyft"},
    {"name": "Twilio", "token": "twilio"},
    {"name": "Elastic", "token": "elastic"},
    {"name": "Asana", "token": "asana"},
    {"name": "Figma", "token": "figma"},
    {"name": "Vercel", "token": "vercel"},
    {"name": "Brex", "token": "brex"},
    {"name": "GitLab", "token": "gitlab"},
    {"name": "Braze", "token": "braze"},
    {"name": "Oscar Health", "token": "oscar"},
    {"name": "Recorded Future", "token": "recordedfuture"},
    {"name": "CarGurus", "token": "cargurus"},
    {"name": "Formlabs", "token": "formlabs"},
    {"name": "Starburst Data", "token": "starburst"},
    {"name": "Betterment", "token": "betterment"},
    {"name": "Squarespace", "token": "squarespace"},
    {"name": "Flatiron Health", "token": "flatironhealth"},
    {"name": "Cockroach Labs", "token": "cockroachlabs"},
    {"name": "Peloton", "token": "peloton"},
    {"name": "Riskified", "token": "riskified"},
    {"name": "Justworks", "token": "justworks"},
    {"name": "ConsenSys", "token": "consensys"},
    {"name": "Greenhouse", "token": "greenhouse"},
    {"name": "TripAdvisor", "token": "tripadvisor"},
    {"name": "Intercom", "token": "intercom"}
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
            return []

        data = res.json()
        raw_jobs = data.get("jobs", [])
        results = []

        for item in raw_jobs:
            title = item.get("title", "").strip()
            loc_obj = item.get("location", {})
            location_str = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)

            loc_info = parse_location_type(location_str)
            city = loc_info["city"]

            if city not in ["New York, NY", "Boston, MA", "Remote"]:
                continue

            title_lower = title.lower()
            engineering_keywords = [
                "software engineer", "software developer", "swe", "backend", "full stack", "fullstack",
                "frontend", "front end", "infrastructure", "systems engineer", "platform engineer",
                "data engineer", "machine learning", "ml engineer", "applied scientist", "ai engineer",
                "research engineer", "member of technical staff", "sre", "site reliability", "cloud engineer",
                "security engineer", "devops", "embedded engineer", "firmware", "distributed systems",
                "architect", "engineering manager", "director of engineering"
            ]
            exclusions = [
                "intern", "internship", "co-op", "fellowship", "student", "sales", "account executive",
                "recruiter", "talent acquisition", "human resources", "hr ", "marketing", "legal",
                "customer support", "office manager"
            ]

            if any(ex in title_lower for ex in exclusions):
                continue

            if not any(k in title_lower for k in engineering_keywords):
                continue

            raw_content = item.get("content", "")
            clean_desc = clean_html(raw_content)

            salary_info = parse_salary(clean_desc)
            yoe_info = parse_yoe(clean_desc)
            tech_stack = parse_tech_stack(clean_desc)
            seniority = parse_seniority(title)
            discipline = parse_discipline(title, clean_desc)
            archetype = parse_job_archetype(title, clean_desc)
            recruiter_info = match_recruiter_for_job(company_name, city, title)

            job_id = f"gh_{board_token}_{item.get('id')}"
            date_posted = parse_exact_date(item.get("updated_at", ""), fallback_seed=job_id)

            snippet = clean_desc[:260] + "..." if len(clean_desc) > 260 else clean_desc

            results.append({
                "id": job_id,
                "title": title,
                "company": company_name,
                "location": location_str,
                "city": city,
                "work_model": loc_info["work_model"],
                "seniority": seniority,
                "discipline": discipline,
                "archetype": archetype,
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

        logger.info(f"Greenhouse [{company_name}]: Found {len(results)} matching positions.")
        return results

    except Exception as e:
        logger.error(f"Error fetching Greenhouse for {company_name}: {e}")
        return []


def scrape_greenhouse_all(boards: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    """Scrapes all configured Greenhouse companies."""
    targets = boards or DEFAULT_GREENHOUSE_BOARDS
    all_jobs = []
    for b in targets:
        time.sleep(0.15)
        jobs = fetch_greenhouse_board(b["token"], b["name"])
        all_jobs.extend(jobs)
    return all_jobs
