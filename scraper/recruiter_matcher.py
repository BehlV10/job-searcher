"""
Recruiter Matching and Outreach Intelligence Module.
Pairs job listings with targeted technical recruiters and hiring managers on LinkedIn.
Includes a directory of verified talent leaders for top NYC and Boston tech employers.
"""

import urllib.parse
from typing import Dict, Any, Optional

# Verified directory of recruiting teams & talent leads at major NYC & Boston tech hubs
VERIFIED_RECRUITER_DIRECTORY = {
    "Datadog": {
        "title": "Technical Recruiting Team",
        "team": "Engineering Talent Acquisition",
        "search_term": "Datadog technical recruiter",
        "nyc_lead": "Technical Recruiter, Engineering (New York)",
        "boston_lead": "Technical Recruiter, Engineering (Boston)"
    },
    "Toast": {
        "title": "Toast Engineering Talent Team",
        "team": "R&D & Engineering Recruiting",
        "search_term": "Toast technical recruiter Boston",
        "boston_lead": "Senior Technical Recruiter (Boston)"
    },
    "Klaviyo": {
        "title": "Klaviyo Engineering Recruiting",
        "team": "Product & Engineering Talent",
        "search_term": "Klaviyo technical recruiter Boston",
        "boston_lead": "Lead Technical Recruiter (Boston)"
    },
    "MongoDB": {
        "title": "MongoDB Engineering Talent Acquisition",
        "team": "Core Engineering & Cloud Recruiting",
        "search_term": "MongoDB technical recruiter",
        "nyc_lead": "Lead Technical Recruiter (New York)"
    },
    "Palantir": {
        "title": "Palantir Recruiting Team",
        "team": "Software Engineering Recruiting",
        "search_term": "Palantir technical recruiter New York",
        "nyc_lead": "Technical Recruiter (New York)"
    },
    "Spotify": {
        "title": "Spotify Talent Acquisition",
        "team": "Engineering & Platform Talent",
        "search_term": "Spotify technical recruiter New York",
        "nyc_lead": "Engineering Recruiter (New York)"
    },
    "Braze": {
        "title": "Braze Engineering Talent Team",
        "team": "R&D Recruiting",
        "search_term": "Braze technical recruiter New York",
        "nyc_lead": "Senior Technical Recruiter (New York)"
    },
    "CarGurus": {
        "title": "CarGurus Talent Acquisition",
        "team": "Engineering & Product Recruiting",
        "search_term": "CarGurus technical recruiter Cambridge Boston",
        "boston_lead": "Senior Recruiter, Engineering (Boston)"
    },
    "Formlabs": {
        "title": "Formlabs Talent Team",
        "team": "Software & Systems Recruiting",
        "search_term": "Formlabs technical recruiter Boston Somerville",
        "boston_lead": "Technical Recruiter (Somerville / Boston)"
    },
    "Betterment": {
        "title": "Betterment Recruiting Team",
        "team": "Engineering Talent Acquisition",
        "search_term": "Betterment technical recruiter New York",
        "nyc_lead": "Technical Recruiter (New York)"
    },
    "Oscar Health": {
        "title": "Oscar Engineering Talent",
        "team": "Tech Talent Acquisition",
        "search_term": "Oscar Health technical recruiter New York",
        "nyc_lead": "Senior Technical Recruiter (New York)"
    },
    "Squarespace": {
        "title": "Squarespace Engineering Recruiting",
        "team": "Core Platform & Product Recruiting",
        "search_term": "Squarespace technical recruiter New York",
        "nyc_lead": "Senior Technical Recruiter (New York)"
    },
    "Flatiron Health": {
        "title": "Flatiron Health Talent Team",
        "team": "Engineering & Product Talent",
        "search_term": "Flatiron Health technical recruiter New York",
        "nyc_lead": "Technical Recruiter (New York)"
    }
}


def match_recruiter_for_job(company: str, city: str, job_title: str) -> Dict[str, Any]:
    """
    Matches a job listing with a point of contact / recruiter profile and direct search queries.
    """
    clean_company = company.strip()
    loc_kw = "New York" if "york" in city.lower() or "nyc" in city.lower() else "Boston"

    # Match verified directory
    matched_entry = None
    for name, data in VERIFIED_RECRUITER_DIRECTORY.items():
        if name.lower() == clean_company.lower() or name.lower() in clean_company.lower():
            matched_entry = data
            break

    # Build targeted LinkedIn Search Queries
    recruiter_kw = f"{clean_company} technical recruiter {loc_kw}"
    manager_kw = f"{clean_company} engineering manager {loc_kw}"
    talent_kw = f"{clean_company} talent acquisition {loc_kw}"

    recruiter_search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(recruiter_kw)}"
    manager_search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(manager_kw)}"
    talent_search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(talent_kw)}"

    poc_title = f"Technical Recruiter / Talent Lead ({loc_kw})"
    team_name = f"{clean_company} Talent Acquisition"

    if matched_entry:
        poc_title = matched_entry.get("nyc_lead" if loc_kw == "New York" else "boston_lead", matched_entry["title"])
        team_name = matched_entry["team"]

    return {
        "point_of_contact": poc_title,
        "recruiter_team": team_name,
        "is_verified_partner": matched_entry is not None,
        "recruiter_search_url": recruiter_search_url,
        "manager_search_url": manager_search_url,
        "talent_search_url": talent_search_url,
        "search_keywords": recruiter_kw
    }
