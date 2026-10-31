"""
Built In Scraper for Built In Boston and Built In NYC.
Scrapes local tech company job boards from Built In's dev-engineering listings.
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
    parse_location_type,
    generate_recruiter_links
)

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

BUILTIN_SITES = [
    {
        "city": "Boston, MA",
        "domain": "www.builtinboston.com",
        "url": "https://www.builtinboston.com/jobs/dev-engineering"
    },
    {
        "city": "New York, NY",
        "domain": "www.builtinnyc.com",
        "url": "https://www.builtinnyc.com/jobs/dev-engineering"
    }
]


def scrape_builtin_site(site_config: Dict[str, str], max_pages: int = 2) -> List[Dict[str, Any]]:
    """Scrapes engineering job listings from Built In Boston or Built In NYC."""
    city_name = site_config["city"]
    domain = site_config["domain"]
    base_url = site_config["url"]

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://{domain}/"
    }

    results = []

    for page in range(1, max_pages + 1):
        page_url = f"{base_url}?page={page}" if page > 1 else base_url
        try:
            res = requests.get(page_url, headers=headers, timeout=12)
            if res.status_code != 200:
                logger.warning(f"Built In [{city_name}] page {page} returned status {res.status_code}")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("div", {"data-id": "job-card"})
            if not cards:
                # Fallback to secondary card class
                cards = soup.find_all("div", class_=re.compile(r"job-bounded-responsive|job-item"))

            logger.info(f"Built In [{city_name}] page {page}: Found {len(cards)} raw cards.")

            for card in cards:
                # Extract Title
                title_elem = (
                    card.find("a", {"data-id": "job-card-title"}) or
                    card.find("h2") or
                    card.find("h3")
                )
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Extract Company
                comp_elem = (
                    card.find("span", {"data-id": "company-title"}) or
                    card.find("a", {"data-id": "company-title"}) or
                    card.find("div", class_=re.compile(r"company-name|employer"))
                )
                company = comp_elem.get_text(strip=True) if comp_elem else ""

                if not title or not company:
                    continue

                # Filter for Software / Engineering roles and Senior / Staff
                title_lower = title.lower()
                swe_terms = ["engineer", "developer", "backend", "full stack", "frontend", "infrastructure", "systems", "architect", "platform"]
                senior_terms = ["senior", "staff", "lead", "principal", "architect", "manager", "head", "sr", "director"]

                is_swe = any(k in title_lower for k in swe_terms)
                is_senior = any(k in title_lower for k in senior_terms)
                if not (is_swe and is_senior):
                    continue

                # Extract Link
                job_link = ""
                if title_elem and title_elem.name == "a" and title_elem.get("href"):
                    job_link = title_elem["href"]
                else:
                    for a in card.find_all("a", href=True):
                        href = a["href"]
                        if "/job/" in href:
                            job_link = href
                            break

                if job_link and not job_link.startswith("http"):
                    job_link = f"https://{domain}{job_link}"

                card_text = card.get_text(" ", strip=True)

                # Parse salary from card text
                salary_info = parse_salary(card_text)
                yoe_info = parse_yoe(card_text)
                tech_stack = parse_tech_stack(card_text)
                seniority = parse_seniority(title)

                # Workplace model
                work_model = "On-site"
                if "remote" in card_text.lower():
                    work_model = "Remote"
                elif "hybrid" in card_text.lower():
                    work_model = "Hybrid"

                recruiter_links = generate_recruiter_links(company, city_name, title)

                job_id = f"builtin_{abs(hash(title + company + city_name))}"

                results.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": city_name,
                    "city": city_name,
                    "work_model": work_model,
                    "seniority": seniority,
                    "source": "Built In",
                    "apply_url": job_link or f"https://{domain}",
                    "date_posted": "Recently",
                    "salary": salary_info,
                    "experience": yoe_info,
                    "tech_stack": tech_stack,
                    "snippet": f"Open {seniority} engineering position at {company} in {city_name} via Built In.",
                    "description": card_text,
                    "recruiter": recruiter_links
                })

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error scraping Built In [{city_name}]: {e}")
            break

    logger.info(f"Built In [{city_name}]: Extracted {len(results)} matching Senior/Staff positions.")
    return results


def scrape_builtin_all() -> List[Dict[str, Any]]:
    """Scrapes Built In Boston and Built In NYC."""
    all_jobs = []
    for site in BUILTIN_SITES:
        jobs = scrape_builtin_site(site, max_pages=2)
        all_jobs.extend(jobs)
    return all_jobs
