"""
Parser module for extracting structured job attributes from unstructured descriptions:
- Salary ranges (annual / hourly, formatted with currency)
- Years of Experience (YoE)
- Tech stack keywords
- Recruiter outreach links
- Location categorization
"""

import re
import urllib.parse
from html import unescape
from typing import Optional, Dict, Any, List


TECH_KEYWORDS = [
    "Python", "Go", "Golang", "Java", "C++", "Rust", "TypeScript", "JavaScript",
    "React", "Node.js", "Kubernetes", "Docker", "AWS", "GCP", "Azure",
    "Kafka", "PostgreSQL", "MySQL", "Redis", "MongoDB", "GraphQL", "REST",
    "Distributed Systems", "Microservices", "CI/CD", "Terraform", "Spark",
    "gRPC", "Elasticsearch", "Cassandra", "Snowflake", "PyTorch", "LLM", "AI"
]


def clean_html(raw_html: str) -> str:
    """Strip basic HTML tags and unescape HTML entities (including double-encoded content)."""
    if not raw_html:
        return ""
    # Greenhouse and some boards return double-encoded HTML (&lt;div&gt;)
    text = unescape(unescape(raw_html))
    # Replace common HTML dash entities before stripping tags
    text = text.replace("&mdash;", "—").replace("&ndash;", "–").replace("&nbsp;", " ")
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Final unescape pass
    text = unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_salary(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts salary information from job text.
    Handles annual amounts ($180k-$220k, $180,000 - $240,000) and hourly rates.
    """
    if not text:
        return None

    cleaned = text.replace("&mdash;", "—").replace("&ndash;", "–")

    # Pattern 1: Standard Range with optional k/K: $180,000 - $240,000 or $180k - $240k or $180,000 to $240,000
    range_pattern = re.compile(
        r"\$\s*(\d{1,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s*[kK])"
        r"\s*(?:[-—–/]|to)\s*"
        r"\$\s*(\d{1,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s*[kK])"
        r"(?:\s*(?:USD|per year|/yr|a year|annually))?",
        re.IGNORECASE
    )

    match = range_pattern.search(cleaned)
    if match:
        min_str, max_str = match.group(1), match.group(2)
        min_val = _normalize_salary_val(min_str)
        max_val = _normalize_salary_val(max_str)

        # Filter out false positives (e.g., small bonus amounts or stock grants under $50k unless hourly)
        if min_val >= 60000 or max_val >= 60000:
            return {
                "min": min_val,
                "max": max_val,
                "currency": "USD",
                "period": "yearly",
                "display": f"${min_val:,.0f} - ${max_val:,.0f} / yr"
            }

    # Pattern 2: Hourly rate ($80 - $120 / hr)
    hourly_pattern = re.compile(
        r"\$\s*(\d{2,3}(?:\.\d{2})?)\s*(?:[-—–]|to)\s*\$\s*(\d{2,3}(?:\.\d{2})?)\s*(?:/(?:hr|hour)|per hour)",
        re.IGNORECASE
    )
    h_match = hourly_pattern.search(cleaned)
    if h_match:
        h_min = float(h_match.group(1))
        h_max = float(h_match.group(2))
        ann_min = int(h_min * 2080)
        ann_max = int(h_max * 2080)
        return {
            "min": ann_min,
            "max": ann_max,
            "currency": "USD",
            "period": "hourly",
            "display": f"${h_min:.0f} - ${h_max:.0f} / hr (${ann_min:,.0f} - ${ann_max:,.0f}/yr)"
        }

    # Pattern 3: Single salary quote ($200,000 base or starting at $190,000)
    single_pattern = re.compile(
        r"(?:base\s*salary(?:\s*of)?|starting\s*at|up\s*to)\s*\$\s*(\d{1,3}(?:,\d{3})+|\d{2,3}\s*[kK])",
        re.IGNORECASE
    )
    s_match = single_pattern.search(cleaned)
    if s_match:
        val = _normalize_salary_val(s_match.group(1))
        if val >= 60000:
            return {
                "min": val,
                "max": val,
                "currency": "USD",
                "period": "yearly",
                "display": f"${val:,.0f}+ / yr"
            }

    return None


def _normalize_salary_val(val_str: str) -> int:
    """Converts '$180k', '180,000', or '180' to integer value in dollars."""
    val_str = val_str.strip().replace(",", "").replace("$", "")
    if val_str.lower().endswith("k"):
        return int(float(val_str[:-1]) * 1000)
    return int(float(val_str))


def parse_yoe(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts years of experience requirement from job text.
    Handles '5+ years', '7-10 years', 'minimum 8 years', etc.
    """
    if not text:
        return None

    patterns = [
        # 7+ years of experience / 5-8 years of software engineering experience
        r"\b(\d{1,2})\s*(?:\+|(?:-|–|to)\s*(\d{1,2}))?\s*years?(?:\s*(?:of\s*)?(?:hands-on|software|engineering|relevant|professional|prior|\s)*experience)",
        # minimum of 5 years / at least 6 years
        r"(?:minimum|at least)\s*(?:of\s*)?(\d{1,2})\s*years?",
        # 5+ years building/working
        r"\b(\d{1,2})\+\s*years?(?:\s+in|\s+with|\s+building|\s+developing|\s+designing)?"
    ]

    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            min_years = int(groups[0])
            max_years = int(groups[1]) if len(groups) > 1 and groups[1] else None

            # Filter unrealistic numbers (e.g., 50 years)
            if 1 <= min_years <= 20:
                if max_years:
                    display = f"{min_years}-{max_years} years"
                else:
                    display = f"{min_years}+ years"
                return {
                    "min_years": min_years,
                    "max_years": max_years,
                    "display": display
                }

    return None


def parse_tech_stack(text: str) -> List[str]:
    """Finds matched tech keywords from standard tech stack."""
    if not text:
        return []
    found = set()
    for tech in TECH_KEYWORDS:
        # Match word boundaries for tech terms
        if tech in ("C++", "CI/CD"):
            escaped = re.escape(tech)
            if re.search(r"(?:\b|\s)" + escaped + r"(?:\b|\s|,|\.)", text, re.IGNORECASE):
                found.add(tech)
        elif tech == "Go" or tech == "Golang":
            # Match Golang, or 'Go' with capital G followed by comma, slash, and, or tech keywords
            if re.search(r"\bGolang\b", text, re.IGNORECASE) or re.search(r"(?:\b(?:Python|Java|C\+\+|Rust)[,\s/]+Go\b|\bGo[,\s/]+(?:Python|Java|Kubernetes|AWS|Docker)\b|\bGo\s+(?:language|engineer|developer|backend)\b)", text):
                found.add("Go")
            elif re.search(r"\bGo\b", text) and "Go" in text:
                # If explicitly capitalized 'Go' in a list of requirements
                found.add("Go")
        else:
            if re.search(r"\b" + re.escape(tech) + r"\b", text, re.IGNORECASE):
                found.add(tech)
    return sorted(list(found))


def parse_seniority(title: str) -> str:
    """Categorizes the role seniority level from title."""
    title_lower = title.lower()
    if "principal" in title_lower or "distinguished" in title_lower or "fellow" in title_lower:
        return "Principal"
    if "staff" in title_lower:
        return "Staff"
    if "lead" in title_lower or "tech lead" in title_lower:
        return "Lead"
    if "senior" in title_lower or "sr." in title_lower or "sr " in title_lower:
        return "Senior"
    if "manager" in title_lower:
        return "Engineering Manager"
    return "Mid/Senior"


def parse_location_type(location: str, description: str = "") -> Dict[str, Any]:
    """Determines location city (NYC, Boston) and workplace type (Remote, Hybrid, On-site)."""
    combined = f"{location} {description}".lower()

    # Metro area
    city = "Other"
    if any(k in combined for k in ["new york", "nyc", "manhattan", "brooklyn"]):
        city = "New York, NY"
    elif any(k in combined for k in ["boston", "cambridge", "somerville", "massachusetts", "ma"]):
        city = "Boston, MA"
    elif "remote" in location.lower():
        city = "Remote"

    # Workplace model
    work_model = "On-site"
    if "remote" in combined:
        work_model = "Remote"
    elif "hybrid" in combined:
        work_model = "Hybrid"

    return {
        "city": city,
        "work_model": work_model
    }


def generate_recruiter_links(company: str, location: str = "New York, NY", job_title: str = "") -> Dict[str, str]:
    """
    Generates tailored LinkedIn search URLs for recruiters and engineering leaders.
    This lets the user immediately jump to the right hiring points of contact.
    """
    encoded_company = urllib.parse.quote(company)
    loc_kw = "New York" if "york" in location.lower() or "nyc" in location.lower() else "Boston"

    recruiter_query = f"{company} technical recruiter {loc_kw}"
    manager_query = f"{company} engineering manager {loc_kw}"
    talent_query = f"{company} talent acquisition"

    return {
        "recruiter_search_url": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(recruiter_query)}",
        "manager_search_url": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(manager_query)}",
        "talent_search_url": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(talent_query)}"
    }
