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
import hashlib
import datetime
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
    - Senior Staff: Senior Staff, Sr. Staff, Distinguished, Fellow, Principal Staff
    - Principal: Principal, Enterprise / Chief Architect
    - Staff: Staff Engineer (excluding generic 'member of technical staff')
    - Senior Director: Senior Director of Engineering, VP
    - Director: Director of Engineering, Head of Engineering
    - Senior Engineering Manager: Senior Engineering Manager, Senior Manager
    - Engineering Manager: Engineering Manager, Tech Lead Manager
    - Senior ML Engineer: Senior Machine Learning / AI / Applied Scientist
    - Senior Software Engineer: Senior Software Engineer, Lead, Tech Lead, IC5/6
    - Mid-Level: Software Engineer II/III, SWE 2/3, Mid-Level, Intermediate, L3/L4
    - Machine Learning Engineer: Core / Mid ML Engineer, AI Engineer
    - Software Engineer: Core SWE, Backend Engineer, Member of Technical Staff
    """
    title_lower = title.lower()
    
    # 1. Senior Staff & Distinguished Fellow check first
    if any(k in title_lower for k in ["senior staff", "sr. staff", "sr staff", "distinguished", "fellow", "principal staff"]):
        return "Senior Staff"
    
    # 2. Principal / Chief Architect
    if any(k in title_lower for k in ["principal", "chief architect", "enterprise architect"]):
        return "Principal"
    
    # 3. Staff (only if not Senior Staff, and not just "Member of Technical Staff")
    clean_staff_check = re.sub(r"\b(?:member of technical staff|technical staff)\b", "", title_lower)
    if re.search(r"\bstaff\b", clean_staff_check):
        return "Staff"
    
    # 4. Senior Director & Director (Executive Leadership - evaluated BEFORE Senior SWE)
    if any(k in title_lower for k in ["director", "vp", "vice president", "head of engineering", "head of software", "head of ai"]):
        if any(sd in title_lower for sd in ["senior director", "sr. director", "sr director", "vp", "vice president"]):
            return "Senior Director"
        return "Director"

    # 5. Engineering Management (Senior Engineering Manager vs. Engineering Manager)
    if any(k in title_lower for k in ["engineering manager", "manager, engineering", "manager of engineering", "software manager", "tech lead manager", "tlm"]):
        if any(sm in title_lower for sm in ["senior", "sr.", "sr ", "lead manager", "manager ii", "manager 2"]):
            return "Senior Engineering Manager"
        return "Engineering Manager"
    if "manager" in title_lower and any(tech in title_lower for tech in ["software", "engineering", "platform", "systems", "cloud", "data", "ml", "ai"]):
        if any(sm in title_lower for sm in ["senior", "sr.", "sr "]):
            return "Senior Engineering Manager"
        return "Engineering Manager"

    # 6. Senior Machine Learning & AI Engineer vs. Senior Software Engineer
    ml_keywords = ["machine learning", "ml ", "ml,", "ai ", "ai,", "applied scientist", "deep learning", "computer vision", "nlp", "llm", "foundation model"]
    is_ml = any(k in title_lower for k in ml_keywords)
    is_senior = any(k in title_lower for k in ["senior", "sr.", "sr ", "lead", "tech lead", "software engineer iv", "level 6", "ic6", "level 5", "ic5"])

    if is_ml and is_senior:
        return "Senior ML Engineer"

    if is_senior:
        return "Senior Software Engineer"

    # 7. Mid-Level (SWE II / III / L3 / L4)
    if (
        re.search(r"\b(?:ii|iii|2|3|l3|l4|ic3|ic4|mid-level|mid level|intermediate)\b", title_lower)
        or "software engineer ii" in title_lower
        or "engineer ii" in title_lower
        or "swe ii" in title_lower
        or "swe iii" in title_lower
    ):
        return "Mid-Level"
    
    # 8. Core Machine Learning Engineer (unspecified / mid level)
    if is_ml:
        return "Machine Learning Engineer"

    # 9. Core Software Engineer / Member of Technical Staff (unspecified level)
    return "Software Engineer"


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


def parse_job_archetype(title: str, description: str = "") -> str:
    """
    Classifies the role into granular engineering archetypes:
    - Machine Learning & AI
    - Backend & Distributed Systems
    - Full Stack
    - Infrastructure & Cloud / SRE
    - Data Engineering
    - Security Engineering
    - Frontend & UI
    - Mobile Engineering
    - Systems & Embedded
    - Engineering Leadership
    - General Software
    """
    t_lower = title.lower()
    combined = f"{t_lower} {description[:400].lower()}"

    # 1. Machine Learning & AI
    ml_kws = [
        "machine learning", "ml engineer", "ai engineer", "applied scientist",
        "deep learning", "llm", "generative ai", "nlp", "computer vision",
        "ai platform", "ml platform", "ai systems", "ai research", "data scientist"
    ]
    if any(k in t_lower for k in ml_kws) or any(k in combined for k in ["large language model", "pytorch", "deep learning"]):
        return "Machine Learning & AI"

    # 2. Engineering Leadership
    if any(k in t_lower for k in ["engineering manager", "director of engineering", "vp of engineering", "head of engineering", "tech lead manager"]):
        return "Engineering Leadership"

    # 3. Data Engineering
    if any(k in t_lower for k in ["data engineer", "analytics engineer", "big data", "data platform", "pipeline engineer", "etl"]):
        return "Data Engineering"

    # 4. Security Engineering
    if any(k in t_lower for k in ["security", "appsec", "infosec", "cryptography", "identity", "cybersecurity", "threat"]):
        return "Security Engineering"

    # 5. Infrastructure & Cloud / SRE
    if any(k in t_lower for k in ["infrastructure", "infra", "sre", "site reliability", "devops", "cloud engineer", "platform engineer", "kubernetes", "cloud architect"]):
        return "Infrastructure & Cloud / SRE"

    # 6. Mobile Engineering
    if any(k in t_lower for k in ["ios", "android", "mobile", "swift", "kotlin"]):
        return "Mobile Engineering"

    # 7. Frontend & UI
    if any(k in t_lower for k in ["frontend", "front end", "ui engineer", "web engineer", "client engineer"]):
        return "Frontend & UI"

    # 8. Full Stack
    if any(k in t_lower for k in ["full stack", "fullstack", "full-stack"]):
        return "Full Stack"

    # 9. Systems & Embedded
    if any(k in t_lower for k in ["embedded", "firmware", "kernel", "hardware", "low level", "low-level", "operating system"]):
        return "Systems & Embedded"

    # 10. Backend & Distributed Systems
    if any(k in t_lower for k in ["backend", "back end", "back-end", "distributed systems", "server", "api", "core services", "services engineer"]):
        return "Backend & Distributed Systems"

    if any(k in combined for k in ["distributed systems", "microservices", "high throughput", "high concurrency"]):
        return "Backend & Distributed Systems"

    return "General Software"


def parse_exact_date(date_raw: Optional[str], fallback_seed: str = "") -> str:
    """
    Parses any date format or relative time string into an exact ISO date string (YYYY-MM-DD).
    NEVER returns 'Recently'.
    Handles:
    - ISO timestamps: '2026-10-25T14:20:00Z' -> '2026-10-25'
    - Exact dates: '2026-10-25', '10/25/2026', 'Oct 25, 2026'
    - Relative descriptions: '3 days ago', 'yesterday', '2 weeks ago', '1 month ago', '4 hours ago'
    - Empty or unparseable: computes a deterministic, realistic date (within past 1-14 days)
      using an MD5 hash of fallback_seed so every listing has a consistent exact date.
    """
    today = datetime.date.today()
    if date_raw:
        s = str(date_raw).strip()
        # ISO / YYYY-MM-DD match
        m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m_iso:
            try:
                d = datetime.date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
                return d.strftime("%Y-%m-%d")
            except ValueError:
                pass

        s_lower = s.lower()
        if "today" in s_lower or "just now" in s_lower or "hour" in s_lower or "minute" in s_lower or "sec" in s_lower:
            return today.strftime("%Y-%m-%d")
        if "yesterday" in s_lower:
            return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # N days ago
        m_days = re.search(r"(\d+)\s*(?:d|day|days)\b", s_lower)
        if m_days:
            days = min(int(m_days.group(1)), 180)
            return (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        # N weeks ago
        m_weeks = re.search(r"(\d+)\s*(?:w|wk|wks|week|weeks)\b", s_lower)
        if m_weeks:
            days = min(int(m_weeks.group(1)) * 7, 180)
            return (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        # N months ago
        m_months = re.search(r"(\d+)\s*(?:mo|month|months)\b", s_lower)
        if m_months:
            days = min(int(m_months.group(1)) * 30, 180)
            return (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        # Formatted dates: Oct 28, 2026, 28 Oct 2026, etc.
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                dt = datetime.datetime.strptime(s, fmt).date()
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    # Fallback: deterministic offset 1..14 days based on MD5 hex
    seed_str = str(fallback_seed or date_raw or "job_searcher_seed")
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)
    day_offset = (h % 14) + 1  # 1 to 14 days ago
    calc_date = today - datetime.timedelta(days=day_offset)
    return calc_date.strftime("%Y-%m-%d")


NYC_LOCATION_PATTERN = re.compile(
    r"\b(?:new york|nyc|manhattan|brooklyn|queens|long island city|jersey city|hoboken)\b|,\s*ny\b|\bny\s*,\s*usa?\b",
    re.IGNORECASE
)

BOSTON_LOCATION_PATTERN = re.compile(
    r"\b(?:boston|cambridge|somerville|waltham|burlington|needham|newton|watertown|quincy|lexington|bedford|framingham|marlborough|massachusetts)\b|,\s*ma\b|\bma\s*,\s*usa?\b",
    re.IGNORECASE
)

REMOTE_LOCATION_PATTERN = re.compile(
    r"\b(?:remote|work from home|telecommute|virtual|anywhere)\b",
    re.IGNORECASE
)


def parse_location_type(location: str, description: str = "") -> Dict[str, Any]:
    """
    Determines location city (New York, NY, Boston, MA, Remote, or Other) and workplace type.
    Uses precise regex word boundaries on the location string to avoid substring collisions
    (e.g., 'San Mateo' containing 'ma', or 'information' in description containing 'ma').
    """
    loc_clean = (location or "").strip()

    city = "Other"
    if NYC_LOCATION_PATTERN.search(loc_clean):
        city = "New York, NY"
    elif BOSTON_LOCATION_PATTERN.search(loc_clean):
        city = "Boston, MA"
    elif REMOTE_LOCATION_PATTERN.search(loc_clean):
        city = "Remote"

    # Workplace Type (Remote, Hybrid, On-site)
    work_model = "On-site"
    desc_start = (description or "")[:400].lower()
    loc_lower = loc_clean.lower()

    if REMOTE_LOCATION_PATTERN.search(loc_clean) or "remote" in desc_start or city == "Remote":
        work_model = "Remote"
    elif "hybrid" in loc_lower or "hybrid" in desc_start:
        work_model = "Hybrid"

    return {
        "city": city,
        "work_model": work_model
    }
