import re


# URL patterns that confirm a direct vacancy page (high confidence)
# Fast-passed before any other check
_GOOD_URL_PATTERNS = [
    r"jobs\.dou\.ua/vacancies/\d+",
    r"djinni\.co/jobs/[\w-]+",
    r"work\.ua/jobs/\d+",
    r"robota\.ua/ua/vacancy/\d+",
    r"rabota\.ua/vacancy/\d+",          # rabota.ua direct vacancy
    r"rabota\.ua/ua/vacancy/\d+",       # rabota.ua with locale prefix
    r"linkedin\.com/jobs/view/[\w-]*\d+",
    r"jooble\.org/\d+",
]

# URL fragments that indicate NOT a direct vacancy page
_BAD_URL_FRAGMENTS = [
    # Search / filter pages
    "search", "query=", "page=", "filter=", "sort=",
    "vacancies?", "jobs?",
    # Job board list pages (not individual vacancies)
    "rabota.ua/search", "work.ua/jobs-",
    "jooble.org/jobs", "jooble.org/en",
    # Category/listing pages on known boards (no numeric vacancy ID)
    "work.ua/jobs/sales", "work.ua/jobs/manager", "work.ua/jobs/developer",  # text slugs = categories
    "dou.ua/lenta",        # DOU news/lenta listing, not vacancies
    "/vacancies/?",        # listing with filters (e.g. DOU ?city=)
    # Company / profile pages (not vacancies)
    "/company/", "/in/",
    # Non-vacancy content
    "resume", "candidate", "cv", "employer",
    "category", "tag/", "/jobs/#",
]

# Content markers that mean the vacancy is no longer active
_DEAD_CONTENT_MARKERS = [
    "archived", "closed", "expired", "vacancy not found",
    "вакансія не знайдена", "вакансія закрита", "вакансія видалена",
    "job no longer available", "position filled",
]

def is_valid_link(link):
    if not link:
        return False

    link_lower = link.lower()

    # Fast-pass known job board patterns first — before any length check
    # Prevents short but valid vacancy URLs from being rejected
    if any(re.search(p, link_lower) for p in _GOOD_URL_PATTERNS):
        return True

    # Reject known bad URL fragments
    if any(frag in link_lower for frag in _BAD_URL_FRAGMENTS):
        return False

    # Minimum length for generic URLs (not matched above)
    if len(link) < 25:
        return False

    # Generic: must have at least 3 path segments (not a homepage/root)
    if link_lower.count("/") < 3:
        return False

    return True


def is_fresh_job(job):
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    return not any(marker in text for marker in _DEAD_CONTENT_MARKERS)


def filter_by_preferences(jobs, prefs):
    if not prefs:
        return jobs

    result = []

    for j in jobs:
        text = (j.get("title", "") + j.get("description", "")).lower()

        # REMOTE
        if prefs.get("remote") == "Remote":
            if "remote" not in text and "віддалено" not in text:
                continue

        # ENGLISH
        if prefs.get("english") == "B2":
            if "english" not in text:
                continue

        result.append(j)

    return result


# --- NEW FILTERS ---

# =========================
# SHARED: Role short labels — used by explain_match and scoring label
# =========================
ROLE_SHORT_NAMES = {
    "Sales Manager":                "Sales",
    "Account Manager":              "Account",
    "Business Development":         "BDM",
    "Business Development Manager": "BDM",
    "Marketing Manager":            "Marketing",
    "Logistics Manager":            "Logistics",
    "Software Developer":           "Developer",
    "HR Manager":                   "HR",
    "Cook":                         "Cook",
    "Chef":                         "Chef",
    "Driver":                       "Driver",
    "Accountant":                   "Finance",
    "Recruiter":                    "Recruiter",
}


# =========================
# SHARED: Skill matching — single source of truth
# Used by explain_match() and calculate_score()
# =========================
def skill_matches(skill, text):
    """
    Returns True if skill is present in text.
    - Single-word skills: exact substring match only (avoids false positives)
    - Multi-word skills: try exact match first, then any significant token (len > 3)
    """
    if skill.lower() in text:
        return True
    tokens = skill.lower().split()
    if len(tokens) > 1:
        return any(len(t) > 3 and t in text for t in tokens)
    return False


# Exclude jobs whose TITLE clearly indicates a non-sales/non-relevant role.
# Rules:
# - Check title only (not description) — description often mentions support/assistant in passing
# - Use word-boundary match to avoid "customer support manager" killing on "support"
# - Only multi-word phrases that are unambiguously irrelevant as job titles
EXCLUDED_TITLE_PHRASES = [
    "call center",
    "call centre",
    "технічна підтримка",
]

def is_not_excluded_role(job):
    title = job.get("title", "").lower()
    return not any(phrase in title for phrase in EXCLUDED_TITLE_PHRASES)


# Phrases that follow a role keyword when it's used figuratively, not as a job title
_BAD_FOLLOW = [
    "of ",          # "driver of growth", "driver of change" — catches virtually all metaphors
    "for growth", "for business", "for change",
]

# Words that precede a role keyword when it's used as a modifier, not a title
_BAD_PRECEDE = [
    "growth", "key", "main", "primary", "business", "revenue", "major",
]

def _keyword_in_title(title, keyword):
    """Word-boundary match in job title — highest confidence signal."""
    pattern = r'\b' + re.escape(keyword) + r'\b'
    return bool(re.search(pattern, title, re.IGNORECASE))

def _keyword_in_desc_safe(desc, keyword):
    """
    Word-boundary match in first 150 chars of description only.
    Rejects matches where the keyword is used figuratively:
    - followed by 'of ...' (driver of growth, driver of change)
    - preceded by abstract modifiers (growth driver, key driver)
    """
    snippet = desc[:150]
    pattern = r'\b' + re.escape(keyword) + r'\b'
    for m in re.finditer(pattern, snippet, re.IGNORECASE):
        after  = snippet[m.end():m.end() + 25].strip()
        before = snippet[max(0, m.start() - 15):m.start()].strip()
        if any(after.startswith(b) for b in _BAD_FOLLOW):
            continue
        if any(before.endswith(b) for b in _BAD_PRECEDE):
            continue
        return True
    return False

# ROLE_CLUSTERS — single source of truth for role matching
# Each key = canonical role name (lowercase)
# Value = all equivalent titles/aliases in English + Ukrainian
# Used by has_role_match() and explain_match() — same logic everywhere
ROLE_CLUSTERS = {
    "sales manager": [
        # Core sales titles
        "account manager", "account executive", "sales executive",
        "sales representative", "sales specialist", "inside sales",
        "business development", "business development manager",
        # Relationship / retention
        "customer success", "customer success manager", "customer success specialist",
        "client success", "client success manager",
        "key account", "key account manager",
        "client manager", "relationship manager", "client partner",
        # Ukrainian + informal
        "менеджер з продажу", "менеджер по продажам", "продажник", "сейлз",
        # Abbreviations / niche
        "bdm", "sales rep", "sales lead",
    ],
    "account manager": [
        "sales manager", "account executive", "business development",
        "customer success", "key account", "менеджер з продажу",
    ],
    "photographer": [
        "photography", "фотограф", "фото", "зйомка", "фотозйомка",
        "videographer", "відеограф", "photo",
    ],
    "cook": [
        "chef", "кухар", "повар", "кондитер", "кухня",
        "pastry chef", "sous chef", "кухар-кондитер",
    ],
    "chef": [
        "cook", "кухар", "повар", "кондитер",
        "sous chef", "pastry chef",
    ],
    "driver": [
        "водій", "delivery driver", "truck driver",
        "кур'єр", "courier", "доставка", "кур'єр-водій",
    ],
    "software developer": [
        "software engineer", "програміст", "розробник",
        "frontend developer", "backend developer", "fullstack developer",
        "fullstack", "devops engineer", "web developer",
    ],
    "marketing manager": [
        "smm manager", "маркетолог",
        "digital marketer", "content manager", "performance marketer",
    ],
    "logistics manager": [
        "логіст", "supply chain",
        "warehouse manager", "operations manager",
    ],
    "accountant": [
        "бухгалтер", "finance manager",
        "фінансовий менеджер", "financial analyst",
    ],
    "recruiter": [
        "рекрутер", "hr manager",
        "talent acquisition", "hr specialist",
    ],
}

def has_role_match(job, profile):
    """
    Returns True if the job is relevant for the profile's roles.
    Uses ROLE_CLUSTERS so aliases, Ukrainian names, and related titles
    all count as a match — same logic used by filter and explain_match.
    """
    roles = profile.get("roles", [])
    if not roles:
        return True  # no roles defined — skip this filter

    title = job.get("title", "").lower()
    desc  = job.get("description", "").lower()

    for role in roles:
        role_lower = role.lower()
        # Build full keyword list: canonical name + all cluster members
        cluster = ROLE_CLUSTERS.get(role_lower, [])
        keywords = list(dict.fromkeys([role_lower] + cluster))  # dedup, preserve order

        for kw in keywords:
            if _keyword_in_title(title, kw):
                return True
            if _keyword_in_desc_safe(desc, kw):
                return True

    return False


# Exclude jobs with a description that is too short to be real
# Exception: Djinni job cards don't expose full description in search results
def _is_djinni(job):
    """Returns True for any known Djinni source spelling."""
    return "djinni" in job.get("source", "").lower()


def has_enough_description(job, min_chars=100):
    # Djinni card snippets are short by design — never filter by length
    if _is_djinni(job):
        return True
    description = job.get("description", "")
    return len(description.strip()) >= min_chars


# Exclude junior roles when profile level is middle or higher
SENIOR_LEVELS = ["middle", "senior", "lead", "principal", "staff"]
JUNIOR_KEYWORDS = ["junior", "trainee", "intern", "entry-level", "entry level"]

def is_not_junior_mismatch(job, profile):
    level = profile.get("level", "").lower()
    if level not in SENIOR_LEVELS:
        return True  # profile is junior or unknown — keep all jobs
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    return not any(kw in text for kw in JUNIOR_KEYWORDS)


# --- PIPELINE ---

def _djinni_count(jobs):
    """Count jobs from any Djinni source variant."""
    return sum(1 for j in jobs if "djinni" in j.get("source", "").lower())


def filter_jobs_pipeline(jobs, profile, city, prefs=None, source_stats=None):
    stats = {
        "original": len(jobs),
        "clean": 0,
        "fresh": 0,
        "relevant": 0,
        "role_match": 0,
        "quality": 0,
        # Djinni debug counters — track at every stage
        "djinni_original": _djinni_count(jobs),
        "djinni_clean": 0,
        "djinni_fresh": 0,
        "djinni_role": 0,
        "djinni_final": 0,
    }

    # 1. LINK VALIDITY
    jobs = [j for j in jobs if is_valid_link(j.get("link"))]
    stats["clean"] = len(jobs)
    stats["djinni_clean"] = _djinni_count(jobs)

    # 2. FRESH (not archived/closed/expired)
    jobs = [j for j in jobs if is_fresh_job(j)]
    stats["fresh"] = len(jobs)
    stats["djinni_fresh"] = _djinni_count(jobs)

    # P3: Count valid jobs per source using explicit source_stats dict
    if source_stats:
        for j in jobs:
            src = j.get("source", "Other")
            if src in source_stats:
                source_stats[src]["valid"] += 1

    # 3. PREFERENCES
    jobs = filter_by_preferences(jobs, prefs)
    stats["relevant"] = len(jobs)

    # 4. ROLE MATCH — soft filter, single pass
    # Each job evaluated once: strong (cluster match) or weak (no match)
    # Broad mode: skip role filter entirely
    is_broad = profile.get("search_mode") == "broad" or not profile.get("roles")
    if is_broad:
        stats["role_match"] = len(jobs)
        stats["role_match_skipped"] = True
    else:
        strong, weak = [], []
        for j in jobs:
            if has_role_match(j, profile):
                strong.append(j)
            else:
                j["_weak_role"] = True  # tag once, here, not in a second pass
                weak.append(j)

        if len(strong) >= 3:
            jobs = strong
            stats["role_match_fallback"] = False
        else:
            jobs = strong + weak[:20]
            stats["role_match_fallback"] = True
            stats["role_match_strong"] = len(strong)
        stats["role_match"] = len(jobs)
    stats["djinni_role"] = _djinni_count(jobs)

    # 5. QUALITY FILTERS
    # P1: NO fallback — if few jobs pass, return few jobs (not pre-filter garbage)
    jobs = [j for j in jobs if is_not_excluded_role(j)]
    jobs = [j for j in jobs if has_enough_description(j)]
    jobs = [j for j in jobs if is_not_junior_mismatch(j, profile)]
    stats["quality"] = len(jobs)
    stats["djinni_final"] = _djinni_count(jobs)

    return jobs, stats