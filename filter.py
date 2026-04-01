import re


# URL patterns that confirm a direct vacancy page (high confidence)
_GOOD_URL_PATTERNS = [
    r"jobs\.dou\.ua/vacancies/\d+",
    r"djinni\.co/jobs/[\w-]+",
    r"work\.ua/jobs/\d+",
    r"robota\.ua/ua/vacancy/\d+",
    r"linkedin\.com/jobs/view/\d+",
    r"jooble\.org/\d+",
]

# URL fragments that indicate NOT a direct vacancy page
_BAD_URL_FRAGMENTS = [
    "search", "query=", "page=", "vacancies?", "jobs?",
    "rabota.ua/search", "work.ua/jobs-",
    "jooble.org/jobs", "jooble.org/en",
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

    # Minimum length — generic/redirect URLs are typically <25 chars
    if len(link) < 25:
        return False

    link_lower = link.lower()

    # Reject known bad URL patterns
    if any(frag in link_lower for frag in _BAD_URL_FRAGMENTS):
        return False

    # Bonus: if URL matches a known direct vacancy pattern, fast-pass
    if any(re.search(p, link_lower) for p in _GOOD_URL_PATTERNS):
        return True

    # Generic acceptance: must have at least 3 path segments (not a homepage)
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

# Exclude jobs with irrelevant/low-quality roles in title or description
EXCLUDED_KEYWORDS = ["support", "call center", "operator", "assistant"]

def is_not_excluded_role(job):
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    return not any(kw in text for kw in EXCLUDED_KEYWORDS)


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

# Maps each English role name to its Ukrainian / alias equivalents
# Rules: multi-word phrases preferred over single words to avoid false positives
# Single words only kept when they are unambiguous role names (chef, cook, кухар, водій)
DOMAIN_KEYWORDS = {
    "cook":              ["кухар", "повар", "chef", "cook", "кондитер"],
    "chef":              ["кухар", "повар", "chef", "cook", "кондитер"],
    "driver":            ["водій", "driver", "truck driver", "delivery driver", "доставка"],
    "logistics manager": ["логіст", "logistics manager", "supply chain"],
    "accountant":        ["бухгалтер", "accountant", "фінансовий менеджер"],
    "recruiter":         ["рекрутер", "recruiter", "talent acquisition", "hr manager"],
    "software developer":["програміст", "розробник", "software developer", "software engineer", "devops engineer", "frontend developer", "backend developer", "fullstack developer"],
    "marketing manager": ["маркетолог", "marketing manager", "smm manager", "digital marketer"],
    "sales manager":     ["продажник", "sales manager", "account manager", "менеджер з продажу", "business development"],
}

def has_role_match(job, profile):
    """
    Returns True if the job is relevant for the profile's roles.

    Matching priority:
    1. Title match (word boundary) — high confidence, no context filter needed
    2. Description match (first 150 chars, word boundary, figurative-use filter)
    3. Ukrainian/alias keywords via DOMAIN_KEYWORDS — same rules apply

    False positive prevention:
    - "driver of growth"  → rejected (followed by "of ")
    - "growth driver"     → rejected (preceded by "growth")
    - "Delivery Driver"   → accepted (title match)
    - "Водій кур'єр"      → accepted (alias "водій" in title)
    """
    roles = profile.get("roles", [])
    if not roles:
        return True  # no roles defined — skip this filter

    title = job.get("title", "").lower()
    desc  = job.get("description", "").lower()

    for role in roles:
        role_lower = role.lower()
        keywords = [role_lower] + DOMAIN_KEYWORDS.get(role_lower, [])

        for kw in keywords:
            # Title match: always trusted
            if _keyword_in_title(title, kw):
                return True
            # Description match: only first 150 chars, reject figurative use
            if _keyword_in_desc_safe(desc, kw):
                return True

    return False


# Exclude jobs with a description that is too short to be real
# Exception: Djinni job cards don't expose full description in search results
def has_enough_description(job, min_chars=100):
    if job.get("source", "") == "Djinni":
        return True  # Djinni only returns card snippets — don't filter by length
    description = job.get("description", "")
    return len(description.strip()) >= min_chars


# Exclude jobs with bad or suspiciously short links
def is_not_bad_link(job, min_length=20):
    link = job.get("link", "")
    if not link or len(link) < min_length:
        return False
    link_lower = link.lower()
    if any(bad in link_lower for bad in ["search", "query"]):
        return False
    return True


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

def filter_jobs_pipeline(jobs, profile, city, prefs=None):
    stats = {
        "original": len(jobs),
        "clean": 0,
        "fresh": 0,
        "relevant": 0,
        "role_match": 0,
        "quality": 0,
    }

    # 1. LINK VALIDITY
    jobs = [j for j in jobs if is_valid_link(j.get("link"))]
    stats["clean"] = len(jobs)

    # 2. FRESH (not archived/closed/expired)
    jobs = [j for j in jobs if is_fresh_job(j)]
    stats["fresh"] = len(jobs)

    # Mark jobs that passed link+freshness as "valid" in source stats
    if prefs and isinstance(prefs, dict) and "source_stats" in prefs:
        for j in jobs:
            src = j.get("source", "Other")
            if src in prefs["source_stats"]:
                prefs["source_stats"][src]["valid"] += 1

    # 3. PREFERENCES
    jobs = filter_by_preferences(jobs, prefs)
    stats["relevant"] = len(jobs)

    # 4. ROLE MATCH — skip entirely if no roles defined or search_mode is broad
    # FALLBACK: if result < 3, keep original list
    is_broad = profile.get("search_mode") == "broad" or not profile.get("roles")
    if is_broad:
        stats["role_match"] = len(jobs)
        stats["role_match_skipped"] = True
    else:
        _before_role = jobs
        jobs = [j for j in jobs if has_role_match(j, profile)]
        if len(jobs) < 3:
            jobs = _before_role
            stats["role_match_fallback"] = True
        stats["role_match"] = len(jobs)

    # 5. QUALITY FILTERS
    # FALLBACK: if result < 5, keep jobs from before this filter group
    _before_quality = jobs
    jobs = [j for j in jobs if is_not_excluded_role(j)]
    jobs = [j for j in jobs if has_enough_description(j)]
    jobs = [j for j in jobs if is_not_bad_link(j)]
    jobs = [j for j in jobs if is_not_junior_mismatch(j, profile)]
    if len(jobs) < 5:
        jobs = _before_quality
        stats["quality_fallback"] = True
    stats["quality"] = len(jobs)

    return jobs, stats