"""
Parser module for extracting structured job attributes from unstructured descriptions:
- Salary ranges (annual / hourly, formatted with currency)
- Years of Experience (YoE)
- Tech stack keywords
- Seniority Level: Senior, Staff, Senior Staff, Principal, Engineering Manager
- Discipline: General Software vs Machine Learning / AI
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
    "gRPC", "Elasticsearch", "Cassandra", "Snowflake", "PyTorch", "TensorFlow",
    "LLM", "AI", "LangChain", "Vector DB", "CUDA", "NLP", "Computer Vision"
]


def clean_html(raw_html: str) -> str:
    """Strip basic HTML tags and unescape HTML entities (including double-encoded content)."""
    if not raw_html:
        return ""
    # Greenhouse and some boards return double-encoded HTML (&lt;div&gt;)
    text = unescape(unescape(raw_html))
    text = text.replace("&mdash;", "—").replace("&ndash;", "–").replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
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

    # Pattern 1: Standard Range with optional k/K: $180,000 - $240,000 or $180k - $240k
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
        if tech in ("C++", "CI/CD"):
            escaped = re.escape(tech)
            if re.search(r"(?:\b|\s)" + escaped + r"(?:\b|\s|,|\.)", text, re.IGNORECASE):
                found.add(tech)
        elif tech == "Go" or tech == "Golang":
            if re.search(r"\bGolang\b", text, re.IGNORECASE) or re.search(r"(?:\b(?:Python|Java|C\+\+|Rust)[,\s/]+Go\b|\bGo[,\s/]+(?:Python|Java|Kubernetes|AWS|Docker)\b|\bGo\s+(?:language|engineer|developer|backend)\b)", text):
                found.add("Go")
            elif re.search(r"\bGo\b", text) and "Go" in text:
                found.add("Go")
        else:
            if re.search(r"\b" + re.escape(tech) + r"\b", text, re.IGNORECASE):
                found.add(tech)
    return sorted(list(found))


def parse_seniority(title: str) -> str:
    """
    Categorizes the role into specific seniority tiers:
    - Senior Staff
    - Principal
    - Staff
    - Senior
    - Engineering Manager
    """
    title_lower = title.lower()
    
    # 1. Senior Staff check first
    if "senior staff" in title_lower or "sr. staff" in title_lower or "sr staff" in title_lower:
        return "Senior Staff"
    
    # 2. Principal / Distinguished / Fellow
    if "principal" in title_lower or "distinguished" in title_lower or "fellow" in title_lower:
        return "Principal"
    
    # 3. Staff (only if not Senior Staff)
    if "staff" in title_lower:
        return "Staff"
    
    # 4. Lead
    if "lead" in title_lower or "tech lead" in title_lower:
        return "Lead"
    
    # 5. Senior
    if "senior" in title_lower or "sr." in title_lower or "sr " in title_lower or "level 6" in title_lower or "ic6" in title_lower:
        return "Senior"
    
    # 6. Engineering Manager
    if "manager" in title_lower or "director" in title_lower or "head" in title_lower:
        return "Engineering Manager"
        
    return "Senior"


def parse_discipline(title: str, description: str = "") -> str:
    """
    Separates Machine Learning & AI Engineering from General Software Engineering.
    """
    combined = f"{title} {description[:300]}".lower()
    ml_keywords = [
        "machine learning", "ml engineer", "ai engineer", "applied scientist",
        "deep learning", "nlp", "computer vision", "llm", "ai platform",
        "ml platform", "generative ai", "data scientist", "ai research",
        "machine learning engineer", "ml infrastructure", "ai systems"
    ]
    if any(k in combined for k in ml_keywords):
        return "Machine Learning / AI"
    return "General Software"


def parse_location_type(location: str, description: str = "") -> Dict[str, Any]:
    """Determines location city (NYC, Boston) and workplace type (Remote, Hybrid, On-site)."""
    combined = f"{location} {description}".lower()

    city = "Other"
    if any(k in combined for k in ["new york", "nyc", "manhattan", "brooklyn"]):
        city = "New York, NY"
    elif any(k in combined for k in ["boston", "cambridge", "somerville", "massachusetts", "ma"]):
        city = "Boston, MA"
    elif "remote" in location.lower():
        city = "Remote"

    work_model = "On-site"
    if "remote" in combined:
        work_model = "Remote"
    elif "hybrid" in combined:
        work_model = "Hybrid"

    return {
        "city": city,
        "work_model": work_model
    }
