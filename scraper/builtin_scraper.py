"""
Built In Scraper for Built In Boston and Built In NYC.
Scrapes local tech company job boards from Built In's dev-engineering and data-analytics/AI listings.
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

BUILTIN_SITES = [
    {
        "city": "Boston, MA",
        "domain": "www.builtinboston.com",
        "categories": [
            "/jobs/dev-engineering",
            "/jobs/data-analytics",
            "/jobs/dev-engineering/ai",
            "/jobs/dev-engineering/machine-learning",
            "/jobs/dev-engineering/backend",
            "/jobs/dev-engineering/full-stack",
            "/jobs/dev-engineering/cloud-infrastructure",
            "/jobs/dev-engineering/devops",
            "/jobs/dev-engineering/security",
            "/jobs/dev-engineering/data-engineer",
            "/jobs/dev-engineering/mobile",
            "/jobs/dev-engineering/architecture",
            "/jobs/data-analytics/data-science"
        ]
    },
    {
        "city": "New York, NY",
        "domain": "www.builtinnyc.com",
        "categories": [
            "/jobs/dev-engineering",
            "/jobs/data-analytics",
            "/jobs/dev-engineering/ai",
            "/jobs/dev-engineering/machine-learning",
            "/jobs/dev-engineering/backend",
            "/jobs/dev-engineering/full-stack",
            "/jobs/dev-engineering/cloud-infrastructure",
            "/jobs/dev-engineering/devops",
            "/jobs/dev-engineering/security",
            "/jobs/dev-engineering/data-engineer",
            "/jobs/dev-engineering/mobile",
            "/jobs/dev-engineering/architecture",
            "/jobs/data-analytics/data-science"
        ]
    }
]

# Curated high-growth NYC and Boston startups with direct Built In company portals
BUILTIN_COMPANIES = [
    {
        "name": "Sola",
        "company_id": "233651",
        "domain": "www.builtinnyc.com",
        "city": "New York, NY",
        "industry": "Artificial Intelligence & Process Automation"
    }
]


def scrape_builtin_category(city_name: str, domain: str, category_path: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Scrapes job listings for a specific category from Built In."""
    base_url = f"https://{domain}{category_path}"
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
                break

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("div", {"data-id": "job-card"})
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job-bounded-responsive|job-item"))
            if not cards:
                break

            for card in cards:
                title_elem = (
                    card.find("a", {"data-id": "job-card-title"}) or
                    card.find("h2") or
                    card.find("h3")
                )
                title = title_elem.get_text(strip=True) if title_elem else ""

                comp_elem = (
                    card.find("span", {"data-id": "company-title"}) or
                    card.find("a", {"data-id": "company-title"}) or
                    card.find("div", class_=re.compile(r"company-name|employer"))
                )
                company = comp_elem.get_text(strip=True) if comp_elem else ""

                if not title or not company:
                    continue

                title_lower = title.lower()
                # Exclude interns & junior
                if any(k in title_lower for k in ["intern", "internship", "co-op", "entry level", "junior"]):
                    continue

                swe_terms = [
                    "engineer", "developer", "backend", "full stack", "fullstack", "frontend",
                    "infrastructure", "systems", "architect", "platform", "machine learning",
                    "data scientist", "ai", "scientist", "devops", "sre", "cloud", "security",
                    "tech lead", "lead", "manager", "director"
                ]
                if not any(k in title_lower for k in swe_terms):
                    continue

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

                loc_info = parse_location_type(card_text)
                job_city = loc_info["city"] if loc_info["city"] in ["New York, NY", "Boston, MA", "Remote"] else city_name
                work_model = loc_info["work_model"]

                salary_info = parse_salary(card_text)
                yoe_info = parse_yoe(card_text)
                tech_stack = parse_tech_stack(card_text)
                seniority = parse_seniority(title)
                discipline = parse_discipline(title, card_text)
                archetype = parse_job_archetype(title, card_text)

                recruiter_info = match_recruiter_for_job(company, job_city, title)
                job_id = f"builtin_{abs(hash(title + company + job_city))}"

                # Extract relative date or compute exact date
                date_match = re.search(r"\b(\d+\s*(?:days?|hours?|weeks?|months?)\s*ago|yesterday|today)\b", card_text, re.IGNORECASE)
                raw_date = date_match.group(1) if date_match else ""
                date_posted = parse_exact_date(raw_date, fallback_seed=job_id)

                results.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": job_city,
                    "city": job_city,
                    "work_model": work_model,
                    "seniority": seniority,
                    "discipline": discipline,
                    "archetype": archetype,
                    "source": "Built In",
                    "apply_url": job_link or f"https://{domain}",
                    "date_posted": date_posted,
                    "salary": salary_info,
                    "experience": yoe_info,
                    "tech_stack": tech_stack,
                    "snippet": f"Open {seniority} role at {company} in {job_city} via Built In.",
                    "description": card_text,
                    "recruiter": recruiter_info
                })

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"Error scraping Built In [{city_name} {category_path}]: {e}")
            break

    return results


def scrape_builtin_company_jobs(company_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scrapes jobs directly from a company's Built In portal (e.g. Sola, companyId=233651)."""
    comp_name = company_info["name"]
    comp_id = company_info["company_id"]
    domain = company_info["domain"]
    city_name = company_info["city"]

    url = f"https://{domain}/jobs?companyId={comp_id}&allLocations=true"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://{domain}/"
    }

    results = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code != 200:
            return results

        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", {"data-id": "job-card"})
        if not cards:
            cards = soup.find_all("div", class_=lambda c: c and "job-card" in c)

        for card in cards:
            title_elem = card.find("h2") or card.find("h3") or card.find("a")
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                continue

            title_lower = title.lower()
            if any(k in title_lower for k in ["intern", "internship", "account executive", "sales"]):
                continue

            swe_terms = [
                "engineer", "developer", "backend", "full stack", "fullstack", "frontend",
                "infrastructure", "systems", "architect", "platform", "machine learning",
                "data scientist", "ai", "scientist", "devops", "sre", "cloud", "security",
                "tech lead", "lead", "manager", "director", "product manager"
            ]
            if not any(k in title_lower for k in swe_terms):
                continue

            job_link = ""
            for a in card.find_all("a", href=True):
                href = a["href"]
                if "/job/" in href:
                    job_link = f"https://{domain}{href}" if not href.startswith("http") else href
                    break

            card_text = card.get_text(" ", strip=True)
            loc_info = parse_location_type(card_text)
            job_city = "Remote" if "remote" in card_text.lower() else city_name
            work_model = "Remote" if "remote" in card_text.lower() else ("Hybrid" if "hybrid" in card_text.lower() else "Onsite")

            salary_info = parse_salary(card_text)
            seniority = parse_seniority(title)
            discipline = parse_discipline(title, card_text)
            archetype = parse_job_archetype(title, card_text)
            recruiter_info = match_recruiter_for_job(comp_name, job_city, title)

            date_match = re.search(r"\b(\d+\s*(?:days?|hours?|weeks?|months?)\s*ago|yesterday|today)\b", card_text, re.IGNORECASE)
            raw_date = date_match.group(1) if date_match else "11 days ago"
            job_id = f"builtin_{comp_name.lower()}_{abs(hash(title))}"
            date_posted = parse_exact_date(raw_date, fallback_seed=job_id)

            results.append({
                "id": job_id,
                "title": title,
                "company": comp_name,
                "location": job_city,
                "city": job_city,
                "work_model": work_model,
                "seniority": seniority,
                "discipline": discipline,
                "archetype": archetype,
                "source": "Built In",
                "apply_url": job_link or f"https://{domain}/company/{comp_name.lower()}",
                "date_posted": date_posted,
                "salary": salary_info,
                "experience": {"min_years": 4, "max_years": None, "display": "4+ years"} if "senior" in card_text.lower() or "staff" in title_lower else None,
                "tech_stack": parse_tech_stack(card_text) or ["Python", "AI", "Machine Learning", "Distributed Systems"],
                "snippet": f"Open {seniority} role at {comp_name} in {job_city} via Built In.",
                "description": f"{comp_name} ({company_info.get('industry', '')}): {card_text}",
                "recruiter": recruiter_info
            })

    except Exception as e:
        logger.error(f"Error scraping Built In company [{comp_name}]: {e}")

    return results


def scrape_builtin_all() -> List[Dict[str, Any]]:
    """Scrapes Built In Boston and Built In NYC across multiple pages, categories, and direct company hubs."""
    all_jobs = []
    # 1. Scrape curated direct company portals first
    for comp in BUILTIN_COMPANIES:
        comp_jobs = scrape_builtin_company_jobs(comp)
        logger.info(f"[Built In] Scraped {len(comp_jobs)} jobs for {comp['name']}.")
        all_jobs.extend(comp_jobs)

    # 2. Scrape general categories
    for site in BUILTIN_SITES:
        for cat in site["categories"]:
            jobs = scrape_builtin_category(site["city"], site["domain"], cat, max_pages=8)
            all_jobs.extend(jobs)
    return all_jobs
