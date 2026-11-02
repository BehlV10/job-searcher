"""
LinkedIn Public Job Scraper.
Uses LinkedIn's guest job search endpoint (no login/credentials required).
Scrapes listings for top 500 software companies including:
Google, Microsoft, Salesforce, AMD, Logitech, Verily, HubSpot, Amazon, Meta, Apple, etc.
plus Senior, Staff, Senior Staff, Principal, and ML Engineering in NYC & Boston.
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

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

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def search_linkedin_jobs(keywords: str, location: str, max_pages: int = 2) -> List[Dict[str, Any]]:
    """
    Searches LinkedIn for jobs using the guest job search endpoint.
    Retrieves multiple pages of job cards.
    """
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    results = []

    for page in range(max_pages):
        start = page * 10
        params = {
            "keywords": keywords,
            "location": location,
            "start": start
        }

        try:
            res = requests.get(base_url, headers=headers, params=params, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break

            for li in cards:
                title_elem = li.find("h3", class_="base-search-card__title")
                company_elem = li.find("h4", class_="base-search-card__subtitle")
                loc_elem = li.find("span", class_="job-search-card__location")
                link_elem = li.find("a", class_="base-card__full-link")
                time_elem = li.find("time")
                salary_elem = li.find("span", class_="job-search-card__salary-info")

                title = title_elem.get_text(strip=True) if title_elem else ""
                company = company_elem.get_text(strip=True) if company_elem else ""
                loc_str = loc_elem.get_text(strip=True) if loc_elem else location
                apply_url = link_elem.get("href", "") if link_elem else ""

                if not title or not company:
                    continue

                clean_url = apply_url.split("?")[0] if apply_url else ""
                job_id_match = re.search(r"-(\d+)$", clean_url) or re.search(r"/view/.*?(\d+)", clean_url)
                job_id = f"li_{job_id_match.group(1)}" if job_id_match else f"li_{abs(hash(title + company))}"

                raw_time = ""
                if time_elem:
                    raw_time = time_elem.get("datetime") or time_elem.get_text(strip=True)
                date_posted = parse_exact_date(raw_time, fallback_seed=job_id)

                salary_badge = salary_elem.get_text(strip=True) if salary_elem else ""
                salary_info = parse_salary(salary_badge) if salary_badge else None

                loc_info = parse_location_type(loc_str)
                city = loc_info["city"]
                if city == "Other":
                    non_target = re.search(r"\b(?:san francisco|san mateo|san jose|los angeles|seattle|austin|chicago|london|sunnyvale|mountain view|toronto|vancouver)\b", loc_str, re.IGNORECASE)
                    if non_target:
                        continue
                    city = "New York, NY" if "york" in location.lower() else "Boston, MA"

                seniority = parse_seniority(title)
                discipline = parse_discipline(title)
                archetype = parse_job_archetype(title)
                recruiter_info = match_recruiter_for_job(company, city, title)

                results.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc_str,
                    "city": city,
                    "work_model": loc_info["work_model"],
                    "seniority": seniority,
                    "discipline": discipline,
                    "archetype": archetype,
                    "source": "LinkedIn",
                    "apply_url": clean_url or apply_url,
                    "date_posted": date_posted,
                    "salary": salary_info,
                    "experience": None,
                    "tech_stack": parse_tech_stack(title),
                    "snippet": f"Open position for {title} at {company} ({loc_str}) via LinkedIn.",
                    "description": "",
                    "recruiter": recruiter_info
                })

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"Error querying LinkedIn: {e}")
            break

    return results


def scrape_linkedin_all(searches: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Runs pure universal role-based searches across all tech companies in NYC and Boston."""
    if searches is None:
        searches = [
            # High-Priority Tech Leaders (Guaranteed ingestion for top employers)
            {"keywords": "Software Engineer Google", "location": "New York, NY"},
            {"keywords": "Software Engineer Google", "location": "Boston, MA"},
            {"keywords": "Software Engineer Microsoft", "location": "New York, NY"},
            {"keywords": "Software Engineer Microsoft", "location": "Boston, MA"},
            {"keywords": "Software Engineer Meta", "location": "New York, NY"},
            {"keywords": "Software Engineer Meta", "location": "Boston, MA"},
            {"keywords": "Software Engineer Apple", "location": "New York, NY"},
            {"keywords": "Software Engineer Apple", "location": "Boston, MA"},
            {"keywords": "Software Engineer Amazon", "location": "New York, NY"},
            {"keywords": "Software Engineer Amazon", "location": "Boston, MA"},
            {"keywords": "Software Engineer NVIDIA", "location": "New York, NY"},
            {"keywords": "Software Engineer NVIDIA", "location": "Boston, MA"},
            {"keywords": "Software Engineer Bloomberg", "location": "New York, NY"},
            {"keywords": "Software Engineer DoorDash", "location": "New York, NY"},
            {"keywords": "Software Engineer Etsy", "location": "New York, NY"},

            # Senior Staff & Principal & Distinguished
            {"keywords": "Senior Staff Software Engineer", "location": "New York, NY"},
            {"keywords": "Senior Staff Software Engineer", "location": "Boston, MA"},
            {"keywords": "Principal Software Engineer", "location": "New York, NY"},
            {"keywords": "Principal Software Engineer", "location": "Boston, MA"},
            {"keywords": "Distinguished Engineer", "location": "New York, NY"},
            {"keywords": "Distinguished Engineer", "location": "Boston, MA"},

            # Staff & Senior & Lead roles
            {"keywords": "Staff Software Engineer", "location": "New York, NY"},
            {"keywords": "Staff Software Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Software Engineer", "location": "New York, NY"},
            {"keywords": "Senior Software Engineer", "location": "Boston, MA"},
            {"keywords": "Lead Software Engineer", "location": "New York, NY"},
            {"keywords": "Lead Software Engineer", "location": "Boston, MA"},

            # Core & Mid-Level Engineering (SWE II / III / General SWE)
            {"keywords": "Software Engineer II", "location": "New York, NY"},
            {"keywords": "Software Engineer II", "location": "Boston, MA"},
            {"keywords": "Software Engineer III", "location": "New York, NY"},
            {"keywords": "Software Engineer III", "location": "Boston, MA"},
            {"keywords": "Software Engineer", "location": "New York, NY"},
            {"keywords": "Software Engineer", "location": "Boston, MA"},

            # Machine Learning & AI
            {"keywords": "Machine Learning Engineer", "location": "New York, NY"},
            {"keywords": "Machine Learning Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Machine Learning Engineer", "location": "New York, NY"},
            {"keywords": "Senior Machine Learning Engineer", "location": "Boston, MA"},
            {"keywords": "Staff Machine Learning Engineer", "location": "New York, NY"},
            {"keywords": "Staff Machine Learning Engineer", "location": "Boston, MA"},
            {"keywords": "AI Engineer", "location": "New York, NY"},
            {"keywords": "AI Engineer", "location": "Boston, MA"},
            {"keywords": "Senior AI Engineer", "location": "New York, NY"},
            {"keywords": "Senior AI Engineer", "location": "Boston, MA"},
            {"keywords": "Applied Scientist", "location": "New York, NY"},
            {"keywords": "Applied Scientist", "location": "Boston, MA"},

            # Core Engineering Disciplines (Distributed Systems, Backend, Infra, Data, SRE)
            {"keywords": "Distributed Systems Engineer", "location": "New York, NY"},
            {"keywords": "Distributed Systems Engineer", "location": "Boston, MA"},
            {"keywords": "Backend Engineer", "location": "New York, NY"},
            {"keywords": "Backend Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Backend Engineer", "location": "New York, NY"},
            {"keywords": "Senior Backend Engineer", "location": "Boston, MA"},
            {"keywords": "Staff Backend Engineer", "location": "New York, NY"},
            {"keywords": "Staff Backend Engineer", "location": "Boston, MA"},
            {"keywords": "Infrastructure Engineer", "location": "New York, NY"},
            {"keywords": "Infrastructure Engineer", "location": "Boston, MA"},
            {"keywords": "Site Reliability Engineer", "location": "New York, NY"},
            {"keywords": "Site Reliability Engineer", "location": "Boston, MA"},
            {"keywords": "Platform Engineer", "location": "New York, NY"},
            {"keywords": "Platform Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Data Engineer", "location": "New York, NY"},
            {"keywords": "Senior Data Engineer", "location": "Boston, MA"},
            {"keywords": "Full Stack Engineer", "location": "New York, NY"},
            {"keywords": "Full Stack Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Full Stack Engineer", "location": "New York, NY"},
            {"keywords": "Senior Full Stack Engineer", "location": "Boston, MA"},
            {"keywords": "Security Engineer", "location": "New York, NY"},
            {"keywords": "Security Engineer", "location": "Boston, MA"},
            {"keywords": "Cloud Engineer", "location": "New York, NY"},
            {"keywords": "Cloud Engineer", "location": "Boston, MA"},
            {"keywords": "Engineering Manager", "location": "New York, NY"},
            {"keywords": "Engineering Manager", "location": "Boston, MA"}
        ]

    all_jobs = []
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _do_search(s):
        return search_linkedin_jobs(s["keywords"], s["location"], max_pages=2)

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_search = {executor.submit(_do_search, s): s for s in searches}
        for future in as_completed(future_to_search):
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Error in search: {e}")

    logger.info(f"[LinkedIn] Completed. Retrieved {len(all_jobs)} jobs across all companies.")
    return all_jobs
