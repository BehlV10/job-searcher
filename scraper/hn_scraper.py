"""
Hacker News "Who is Hiring?" Dynamic Job Scraper.
Fetches the monthly "Ask HN: Who is hiring?" thread from the official Hacker News API.
Dynamically discovers tech startups, scale-ups, and companies hiring in NYC, Boston, and US Remote
with ZERO hardcoded company names.
"""

import re
import html
import time
import logging
import requests
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

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

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def fetch_hn_comment(item_id: int) -> Dict[str, Any]:
    """Fetches a single Hacker News item by ID."""
    try:
        res = requests.get(f"{HN_API_BASE}/item/{item_id}.json", timeout=6)
        if res.status_code == 200:
            return res.json() or {}
    except Exception:
        pass
    return {}


def parse_hn_job_comment(comment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses a top-level 'Who is hiring?' comment into one or more structured job dicts.
    Standard HN format:
    Company Name | Role Title | Location | Remote/Onsite | Salary / URL / Tech Stack
    """
    raw_text = comment.get("text", "")
    if not raw_text:
        return []

    comment_id = comment.get("id")
    timestamp = comment.get("time")  # unix epoch

    # Clean HTML formatting
    unescaped = html.unescape(raw_text)
    paragraphs = [p.strip() for p in re.split(r"<p>|<br\s*/?>", unescaped) if p.strip()]
    if not paragraphs:
        return []

    header = re.sub(r"<[^>]+>", "", paragraphs[0]).strip()
    full_text = clean_html(unescaped)

    # Location check: Must be relevant to NYC, Boston, or US Remote
    header_lower = header.lower()
    full_lower = full_text[:400].lower()
    combined_check = f"{header_lower} {full_lower}"

    is_target_location = any(
        loc in combined_check for loc in [
            "new york", "nyc", "brooklyn", "manhattan",
            "boston", "cambridge", "massachusetts", "seaport", "kendall",
            "remote", "us remote", "remote (us"
        ]
    )
    if not is_target_location:
        return []

    # Parse company and initial title from header
    # Common separators: '|', '—', '–', '-'
    parts = [p.strip() for p in re.split(r"[|—–]", header) if p.strip()]
    if not parts:
        return []

    company = parts[0]
    # Clean company name
    company = re.sub(r"\([^)]*\)", "", company).strip()
    if not company or len(company) > 50:
        company = "Tech Startup"

    # Infer city / location
    loc_info = parse_location_type(header)
    city = loc_info["city"]
    work_model = loc_info["work_model"]

    if city not in ["New York, NY", "Boston, MA", "Remote"]:
        # Fallback check on full text
        loc_fallback = parse_location_type(full_text[:300])
        city = loc_fallback["city"]
        work_model = loc_fallback["work_model"]
        if city not in ["New York, NY", "Boston, MA", "Remote"]:
            city = "Remote"
            work_model = "Remote"

    # Extract apply URL: Look for first href or email in text
    url_match = re.search(r'href=["\'](https?://[^"\'>]+)["\']', raw_text)
    apply_url = url_match.group(1) if url_match else f"https://news.ycombinator.com/item?id={comment_id}"

    # Extract roles mentioned
    swe_terms = [
        "software engineer", "developer", "backend", "full stack", "fullstack", "frontend",
        "infrastructure", "systems", "platform", "machine learning", "ml engineer", "ai engineer",
        "data engineer", "sre", "reliability", "cloud", "security engineer", "devops",
        "engineering manager", "lead", "architect"
    ]

    # Check header parts for role title
    candidate_titles = []
    if len(parts) > 1:
        for p in parts[1:]:
            p_clean = re.sub(r"<[^>]+>", "", p).strip()
            if any(t in p_clean.lower() for t in swe_terms) and not any(ex in p_clean.lower() for ex in ["intern", "sales"]):
                candidate_titles.append(p_clean)

    if not candidate_titles:
        # Check text paragraphs for bulleted positions
        for line in full_text.split("\n"):
            line_clean = line.strip(" -*•")
            if any(t in line_clean.lower() for t in swe_terms) and len(line_clean) < 70:
                candidate_titles.append(line_clean)
                break

    if not candidate_titles:
        if any(t in header_lower for t in swe_terms):
            candidate_titles = ["Software Engineer"]
        else:
            return []

    parsed_jobs = []
    for idx, role_title in enumerate(candidate_titles[:2]):  # take up to 2 distinct roles per comment
        job_id = f"hn_{comment_id}_{idx}"
        date_posted = parse_exact_date(str(timestamp), fallback_seed=job_id)
        salary_info = parse_salary(full_text)
        yoe_info = parse_yoe(full_text)
        tech_stack = parse_tech_stack(full_text)
        seniority = parse_seniority(role_title)
        discipline = parse_discipline(role_title, full_text)
        archetype = parse_job_archetype(role_title, full_text)
        recruiter_info = match_recruiter_for_job(company, city, role_title)

        snippet = full_text[:280] + "..." if len(full_text) > 280 else full_text

        parsed_jobs.append({
            "id": job_id,
            "title": role_title,
            "company": company,
            "location": f"{city} ({work_model})",
            "city": city,
            "location_type": city,
            "work_model": work_model,
            "date_posted": date_posted,
            "apply_url": apply_url,
            "url": apply_url,
            "salary": salary_info,
            "experience": yoe_info,
            "tech_stack": tech_stack,
            "seniority": seniority,
            "discipline": discipline,
            "archetype": archetype,
            "source": "Hacker News",
            "description": full_text,
            "snippet": snippet,
            "recruiter": recruiter_info
        })

    return parsed_jobs


def scrape_hn_whoishiring(max_comments: int = 250) -> List[Dict[str, Any]]:
    """
    Scrapes the latest monthly 'Ask HN: Who is hiring?' thread.
    Retrieves job postings dynamically across all tech startups.
    """
    logger.info("Searching Hacker News 'Who is hiring?' for dynamic startup roles...")
    try:
        user_res = requests.get(f"{HN_API_BASE}/user/whoishiring.json", timeout=10)
        if user_res.status_code != 200:
            logger.warning("Could not reach Hacker News whoishiring user.")
            return []

        submitted = user_res.json().get("submitted", [])
        if not submitted:
            return []

        # Find the latest "Who is hiring?" story
        thread_id = None
        for item_id in submitted[:8]:
            story = requests.get(f"{HN_API_BASE}/item/{item_id}.json", timeout=6).json()
            if story and "Who is hiring?" in story.get("title", ""):
                thread_id = item_id
                logger.info(f"Found active HN thread: '{story.get('title')}' (ID: {thread_id})")
                break

        if not thread_id:
            logger.warning("No active HN Who is hiring thread found.")
            return []

        story_data = requests.get(f"{HN_API_BASE}/item/{thread_id}.json", timeout=8).json()
        comment_ids = story_data.get("kids", [])[:max_comments]

        logger.info(f"Parsing {len(comment_ids)} startup postings from Hacker News...")

        jobs = []
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_id = {executor.submit(fetch_hn_comment, cid): cid for cid in comment_ids}
            for future in as_completed(future_to_id):
                comment = future.result()
                if comment and not comment.get("deleted") and not comment.get("dead"):
                    parsed = parse_hn_job_comment(comment)
                    jobs.extend(parsed)

        logger.info(f"[Hacker News] Completed. Retrieved {len(jobs)} dynamic startup roles.")
        return jobs

    except Exception as e:
        logger.error(f"Error scraping Hacker News Who is Hiring: {e}")
        return []
