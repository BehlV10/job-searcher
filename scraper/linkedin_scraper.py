"""
LinkedIn Public Job Scraper.
Uses LinkedIn's guest job search API (no login/credentials required).
Scrapes listings for Senior and Staff SWE positions in NYC and Boston.
"""

import re
import time
import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

from scraper.parser import (
    clean_html,
    parse_salary,
    parse_yoe,
    parse_tech_stack,
    parse_seniority,
    parse_location_type,
    generate_recruiter_links
)

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
                logger.warning(f"LinkedIn search returned status {res.status_code} for {keywords} in {location}")
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

                # Clean tracking params from apply URL
                clean_url = apply_url.split("?")[0] if apply_url else ""

                # Extract job ID
                job_id_match = re.search(r"-(\d+)$", clean_url) or re.search(r"/view/.*?(\d+)", clean_url)
                job_id = f"li_{job_id_match.group(1)}" if job_id_match else f"li_{abs(hash(title + company))}"

                # Date
                date_posted = "Recently"
                if time_elem:
                    date_posted = time_elem.get("datetime") or time_elem.get_text(strip=True)

                # Check if salary was provided in card badge
                salary_badge = salary_elem.get_text(strip=True) if salary_elem else ""
                salary_info = parse_salary(salary_badge) if salary_badge else None

                loc_info = parse_location_type(loc_str)
                city = loc_info["city"]
                if city == "Other":
                    city = "New York, NY" if "york" in location.lower() else "Boston, MA"

                seniority = parse_seniority(title)
                recruiter_links = generate_recruiter_links(company, city, title)

                results.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc_str,
                    "city": city,
                    "work_model": loc_info["work_model"],
                    "seniority": seniority,
                    "source": "LinkedIn",
                    "apply_url": clean_url or apply_url,
                    "date_posted": date_posted,
                    "salary": salary_info,
                    "experience": None,  # Can be populated if description fetched
                    "tech_stack": parse_tech_stack(title),
                    "snippet": f"Open position for {title} at {company} ({loc_str}).",
                    "description": "",
                    "recruiter": recruiter_links
                })

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error querying LinkedIn: {e}")
            break

    logger.info(f"LinkedIn: Retrieved {len(results)} jobs for '{keywords}' in {location}")
    return results


def scrape_linkedin_all(searches: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Runs default searches for NYC and Boston Senior/Staff engineering roles."""
    if searches is None:
        searches = [
            {"keywords": "Staff Software Engineer", "location": "New York, NY"},
            {"keywords": "Senior Software Engineer", "location": "New York, NY"},
            {"keywords": "Staff Software Engineer", "location": "Boston, MA"},
            {"keywords": "Senior Software Engineer", "location": "Boston, MA"}
        ]

    all_jobs = []
    for s in searches:
        jobs = search_linkedin_jobs(s["keywords"], s["location"], max_pages=2)
        all_jobs.extend(jobs)
    return all_jobs
