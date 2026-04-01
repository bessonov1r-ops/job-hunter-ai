import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "sources"))


# Canonical source names — all job sources normalize to one of these
CANONICAL_SOURCES = ["Djinni", "Work.ua", "Robota.ua", "DOU",
                     "LinkedIn", "Jooble", "Search/Web", "Other"]


def normalize_source(raw, link=""):
    """Map any raw source string or link to a canonical source name."""
    raw  = (raw  or "").lower()
    link = (link or "").lower()

    if "djinni"     in raw or "djinni.co"   in link: return "Djinni"
    if "work.ua"    in raw or "work.ua"     in link: return "Work.ua"
    if "robota"     in raw or "robota.ua"   in link: return "Robota.ua"
    if "rabota"     in raw or "rabota.ua"   in link: return "Robota.ua"
    if "dou"        in raw or "dou.ua"      in link: return "DOU"
    if "linkedin"   in raw or "linkedin.com" in link: return "LinkedIn"
    if "jooble"     in raw or "jooble"      in link: return "Jooble"
    if "serp"       in raw or "google"      in raw:  return "Search/Web"
    if "search/web" in raw or "search"      in raw:  return "Search/Web"
    return "Other"


def build_search_queries(profile):
    """
    Build search queries for the PRIMARY role only (roles[0]).
    Other roles are used for filtering/scoring, not for search.
    Returns 1-2 queries: canonical role name + one English alias from its cluster.
    """
    from filter_jobs import ROLE_CLUSTERS

    roles = profile.get("roles", [])
    if not roles:
        return ["sales manager"]  # broad mode fallback

    # PRIMARY ROLE ONLY — first role is the most specific signal
    primary = roles[0]
    cluster = ROLE_CLUSTERS.get(primary.lower(), [])

    queries = [primary]

    # Add one English alias from the cluster (skip Ukrainian, skip short words)
    for alias in cluster:
        if alias != primary.lower() and alias.isascii() and len(alias) > 3:
            queries.append(alias)
            break

    return queries


def collect_jobs(profile, city):
    jobs = []
    stats = {src: {"found": 0, "valid": 0, "final": 0}
             for src in CANONICAL_SOURCES}

    roles  = profile.get("roles", [])
    role   = roles[0] if roles else ""

    # Build role-specific search queries from ROLE_CLUSTERS
    queries = build_search_queries(profile)
    primary_query = queries[0]
    print(f"SEARCH QUERIES: {queries}")

    # DJINNI — search each query, merge results
    try:
        from sources.djinni import get_djinni_jobs
        djinni_jobs = []
        seen_links = set()
        for q in queries:
            batch = get_djinni_jobs(q)
            for job in batch:
                lnk = job.get("link", "")
                if lnk not in seen_links:
                    seen_links.add(lnk)
                    job["source"] = "Djinni"
                    djinni_jobs.append(job)
        print(f"DJINNI RAW: {len(djinni_jobs)}")
        stats["Djinni"]["found"] = len(djinni_jobs)
        jobs.extend(djinni_jobs)
    except Exception as e:
        print(f"Djinni error: {e}")

    # JOOBLE
    try:
        from jooble_jobs import search_jooble_jobs
        j = search_jooble_jobs(primary_query, city)
        for job in j:
            job["source"] = normalize_source(job.get("source", "Jooble"), job.get("link", ""))
            stats[job["source"]]["found"] += 1
        jobs.extend(j)
    except Exception as e:
        print("Jooble error:", e)

    # DOU
    try:
        from dou_jobs import search_dou_jobs
        j = search_dou_jobs(primary_query)
        for job in j:
            job["source"] = normalize_source(job.get("source", "DOU"), job.get("link", ""))
            stats[job["source"]]["found"] += 1
        jobs.extend(j)
    except Exception as e:
        print("DOU error:", e)

    # SERP — primary role + city for localization
    # Generic words like "manager" are forbidden as sole match signal
    _GENERIC_WORDS = {"manager", "specialist", "officer", "coordinator",
                      "assistant", "director", "lead", "head", "chief"}
    try:
        from serp_jobs import search_serp_jobs
        serp_city = city or "Ukraine"
        serp_query = f"{primary_query} {serp_city}"
        j = search_serp_jobs(serp_query, city)

        # Build smart keyword: main non-generic token from primary_query
        tokens = primary_query.lower().split()
        main_kw = next((t for t in tokens if t not in _GENERIC_WORDS and len(t) >= 4),
                       tokens[-1] if tokens else "")

        for job in j:
            title_lower = job.get("title", "").lower()
            # Pass 1: full phrase match (most reliable)
            full_match = primary_query.lower() in title_lower
            # Pass 2: main keyword stem match (catches photographer/photography, cook/cooking)
            # Uses 6-char prefix to avoid over-matching short words
            stem = main_kw[:6] if len(main_kw) >= 6 else main_kw
            kw_match = main_kw and (
                main_kw in title_lower or
                any(word[:6] == stem for word in title_lower.split() if len(word) >= 6)
            )
            if full_match or kw_match:
                job["source"] = normalize_source(job.get("source", "SerpAPI"), job.get("link", ""))
                stats[job["source"]]["found"] += 1
                jobs.append(job)
            else:
                print(f"SERP filtered: {job.get('title', '')[:50]}")
    except Exception as e:
        print("Serp error:", e)

    # FALLBACK: if too few results, retry with extended query (same role, never mixing)
    _FALLBACK_CONTEXT = {
        "photographer": "photographer jobs",
        "cook":         "cook restaurant",
        "chef":         "chef restaurant",
        "driver":       "driver job delivery",
        "baker":        "baker bakery",
        "teacher":      "teacher school",
        "lawyer":       "lawyer jobs",
        "doctor":       "doctor jobs",
        "nurse":        "nurse hospital",
    }
    if len(jobs) < 5 and primary_query:
        fallback_q = _FALLBACK_CONTEXT.get(primary_query.lower(),
                                            primary_query + " jobs")
        print(f"FALLBACK SEARCH: '{fallback_q}' (only {len(jobs)} results so far)")
        try:
            from sources.djinni import get_djinni_jobs
            extra = get_djinni_jobs(fallback_q)
            existing_links = {j.get("link") for j in jobs}
            for job in extra:
                if job.get("link") not in existing_links:
                    job["source"] = "Djinni"
                    jobs.append(job)
                    stats["Djinni"]["found"] += 1
            print(f"FALLBACK added: {len(extra)} extra Djinni jobs")
        except Exception as e:
            print(f"Fallback error: {e}")

    # PRIORITY SORT before returning:
    # 1. Title contains full primary query (exact match first)
    # 2. Djinni source (most reliable for UA market)
    # 3. Description length (more info = better quality)
    pq_lower = primary_query.lower()
    jobs = sorted(jobs, key=lambda j: (
        pq_lower in j.get("title", "").lower(),
        j.get("source") == "Djinni",
        len(j.get("description", "")),
    ), reverse=True)

    return jobs, stats