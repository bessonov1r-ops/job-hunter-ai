from filter_jobs import has_role_match, skill_matches, _keyword_in_title


def _role_score(job, profile):
    """
    Returns (role_points, title_hit, desc_hit).

    title_hit: cluster-aware word-boundary match in title only (+35)
    desc_hit:  cluster-aware match in description only — checked ONLY when title misses (+15)
               desc_hit is NOT set on title match (no bonus for weak descriptions)

    This prevents quality_bonus firing on jobs that only matched via title
    but have irrelevant descriptions.
    """
    from filter_jobs import ROLE_CLUSTERS, _keyword_in_desc_safe

    roles = profile.get("roles", [])
    if not roles:
        return 0, False, False

    title = job.get("title", "").lower()
    desc  = job.get("description", "").lower()

    # Pass 1: title only — cluster-aware, word boundary
    for role in roles:
        role_lower = role.lower()
        cluster    = ROLE_CLUSTERS.get(role_lower, [])
        keywords   = list(dict.fromkeys([role_lower] + cluster))
        for kw in keywords:
            if _keyword_in_title(title, kw):
                # Title match confirmed — desc_hit stays False intentionally
                # bonus (role + 2 skills) only fires when desc also confirms the role
                return 35, True, False

    # Pass 2: description only — reuse desc-safe check directly, no title re-check
    for role in roles:
        role_lower = role.lower()
        cluster    = ROLE_CLUSTERS.get(role_lower, [])
        keywords   = list(dict.fromkeys([role_lower] + cluster))
        for kw in keywords:
            if _keyword_in_desc_safe(desc, kw):
                return 15, False, True

    return 0, False, False


def calculate_score(job, profile, city):
    """
    Single source of truth for base scoring.
    All weights and penalties live here only — smart_score calls this, never duplicates it.

    Weights:
      ROLE  max 35 — title match +35, desc only +15, none penalty
      SKILL max 30 — +6/skill capped
      GEO   max 20 — city +20, remote +12
      BONUS     +5 — role AND 2+ skills
      PENALTIES     — source, link, level mismatch, role/skill absence
    """
    text     = f"{job.get('title', '')} {job.get('description', '')}".lower()
    is_broad = profile.get("search_mode") == "broad" or not profile.get("roles")

    # --- ROLE ---
    if is_broad:
        # Neutral base of 10 given upfront — skills/geo add on top, penalties reduce from here
        # This avoids the "rescue after penalties" pattern and makes scoring more honest
        role_pts, title_hit, desc_hit = 10, False, False
    else:
        role_pts, title_hit, desc_hit = _role_score(job, profile)

    # --- SKILLS ---
    skills        = profile.get("skills", [])
    matched_skills = sum(1 for s in skills if skill_matches(s, text))
    skill_pts     = min(matched_skills * 6, 30)

    # --- GEO ---
    from geo_filter import is_relevant_city
    if is_relevant_city(job, city):
        geo_pts = 20 if (city and city.lower() in text) else 12
    else:
        geo_pts = 0

    # --- QUALITY BONUS ---
    # Fires when role confirmed in description AND 2+ skills matched
    # OR when role in title AND 2+ skills in description (strong combined signal)
    bonus = 5 if (desc_hit or title_hit) and matched_skills >= 2 else 0

    # --- PENALTIES ---
    penalties = 0

    if not is_broad:
        if not desc_hit and not title_hit:
            # No role signal at all — strong penalty
            penalties += 5 if job.get("_weak_role") else 20
        elif not desc_hit and title_hit:
            # Title matched but desc has no role signal — mild penalty
            penalties += 5

    # Skills penalty only in non-broad mode
    if not is_broad and skills and matched_skills == 0:
        penalties += 10

    # Source/link/level penalties skipped in broad mode — exploration, not precision
    if not is_broad:
        source = job.get("source", "").lower()
        if not source or "unknown" in source:
            penalties += 5
        elif "serp" in source or "search" in source:
            penalties += 5

        link = job.get("link", "")
        if not link or link.count("/") < 3:
            penalties += 3

        level = profile.get("level", "").lower()
        if "junior" in text and level in ["middle", "senior"]:
            penalties += 15

    total = role_pts + skill_pts + geo_pts + bonus - penalties

    # Weak-role fallback jobs — floor of 5 prevents penalty stacking to 0
    # Keeps them visible below strong matches but above true garbage
    if job.get("_weak_role") and total < 5:
        total = 5

    return max(0, min(100, total))


def smart_score(job, profile, reasons, warnings, city=""):
    """
    ISSUE 2 FIX: smart_score no longer duplicates calculate_score.
    It calls calculate_score() for the base, then applies only small UI-level
    adjustments from explain_match() signals (reasons/warnings).

    Before: full scoring logic duplicated here (~40 lines)
    After:  one call to calculate_score() + 2 tiny UI bonuses
    """
    base = calculate_score(job, profile, city)

    # Small UI adjustments based on confirmed explain_match signals
    # These are intentionally minor — base score already captures the real signals
    ui_bonus = 0
    if any(r.startswith("🎯") for r in reasons):
        ui_bonus += 3   # UI confirmed role match — small confidence boost
    if any(r.startswith("📍") for r in reasons):
        ui_bonus += 2   # UI confirmed city — small geo boost

    final = max(0, min(100, base + ui_bonus))

    if final >= 70:
        label = "Strong match"
    elif final >= 40:
        label = "Good match"
    else:
        label = "Weak match"

    return {
        "score":     final,
        "label":     label,
        "breakdown": {
            "base":     base,
            "ui_bonus": ui_bonus,
        },
    }