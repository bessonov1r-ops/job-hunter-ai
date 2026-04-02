import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "sources"))

CANONICAL_SOURCES = ["Djinni", "Work.ua", "Robota.ua", "DOU",
                     "LinkedIn", "Jooble", "Search/Web", "Other"]


def normalize_source(raw, link=""):
    raw  = (raw  or "").lower()
    link = (link or "").lower()

    if "djinni" in raw or "djinni.co" in link: return "Djinni"
    if "work.ua" in raw or "work.ua" in link: return "Work.ua"
    if "robota" in raw or "robota.ua" in link: return "Robota.ua"
    if "dou" in raw or "dou.ua" in link: return "DOU"
    if "linkedin" in raw or "linkedin.com" in link: return "LinkedIn"
    if "jooble" in raw or "jooble" in link: return "Jooble"
    return "Other"


def build_search_queries(profile):
    from filter_jobs import ROLE_CLUSTERS

    roles = profile.get("roles", [])
    if not roles:
        return ["sales manager"]

    primary = roles[0]
    cluster = ROLE_CLUSTERS.get(primary.lower(), [])

    queries = [primary]

    for alias in cluster:
        if alias != primary.lower() and alias.isascii() and len(alias) > 3:
            queries.append(alias)
            break

    return queries


# 🔥 УЛУЧШЕНА ПРОВЕРКА ЛИНКА
def is_valid_workua_link(link):
    if not link:
        return False

    link = link.lower().strip()

    # тільки прямі вакансії
    if not link.startswith("https://www.work.ua/jobs/"):
        return False

    # має бути ID
    parts = link.split("/")
    if not any(p.isdigit() for p in parts):
        return False

    # відсікаємо search типу jobs-kyiv
    if "jobs-" in link:
        return False

    return True


def collect_jobs(profile, city):
    jobs = []
    stats = {src: {"found": 0, "valid": 0, "final": 0}
             for src in CANONICAL_SOURCES}

    queries = build_search_queries(profile)
    primary_query = queries[0]

    print(f"SEARCH: {queries}")

    # =========================
    # DJINNI
    # =========================
    try:
        from sources.djinni import get_djinni_jobs

        seen = set()
        djinni_jobs = []

        for q in queries:
            batch = get_djinni_jobs(q)
            for job in batch:
                link = job.get("link", "")
                if link and link not in seen:
                    seen.add(link)
                    job["source"] = "Djinni"
                    djinni_jobs.append(job)

        stats["Djinni"]["found"] = len(djinni_jobs)
        jobs.extend(djinni_jobs)

    except Exception as e:
        print("Djinni error:", e)

    # =========================
    # DOU
    # =========================
    try:
        from dou_jobs import search_dou_jobs
        batch = search_dou_jobs(primary_query)

        for job in batch:
            job["source"] = "DOU"
            jobs.append(job)
            stats["DOU"]["found"] += 1

    except Exception as e:
        print("DOU error:", e)

    # =========================
    # JOOBLE
    # =========================
    try:
        from jooble_jobs import search_jooble_jobs
        batch = search_jooble_jobs(primary_query, city)

        for job in batch:
            job["source"] = "Jooble"
            jobs.append(job)
            stats["Jooble"]["found"] += 1

    except Exception as e:
        print("Jooble error:", e)

    # =========================
    # WORK.UA — ФІНАЛ ФІКС
    # =========================
    try:
        from workua_jobs import get_workua_jobs

        batch = get_workua_jobs(primary_query, city)

        valid_count = 0

        for job in batch:
            link = (job.url or "").strip()

            if not is_valid_workua_link(link):
                print("❌ BAD WORK LINK:", link)
                continue

            job_dict = {
                "title": job.title,
                "company": job.company,
                "city": job.city,
                "link": link,
                "salary": job.salary,
                "source": "Work.ua"
            }

            jobs.append(job_dict)
            valid_count += 1

        stats["Work.ua"]["found"] = len(batch)
        stats["Work.ua"]["valid"] = valid_count

        print(f"WORK.UA VALID: {valid_count}")

    except Exception as e:
        print("Work.ua error:", e)

    # =========================
    # CLEAN DUPLICATES
    # =========================
    seen = set()
    unique = []

    for j in jobs:
        link = j.get("link", "")
        if link and link not in seen:
            seen.add(link)
            unique.append(j)

    jobs = unique

    return jobs, stats