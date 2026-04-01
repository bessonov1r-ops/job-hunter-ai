import requests
import streamlit as st

ROLE_TO_KEYWORDS = {
    "sales manager": ["sales manager", "sales"],
    "account manager": ["account manager", "customer success"],
    "business development manager": ["business development", "bdm"],
    "project manager": ["project manager"],
    "python developer": ["python developer"],
    "frontend developer": ["frontend developer"],
    "fullstack developer": ["fullstack developer"],
    "devops engineer": ["devops"],
    "qa engineer": ["qa engineer"],
    "data analyst": ["data analyst"],
    "marketing manager": ["marketing"],
    "hr manager": ["recruiter", "hr"],
    "ui/ux designer": ["ux designer"],
    "бухгалтер": ["accountant"],
    "логіст": ["logistics"],
    "кухар": ["chef"],
    "водій": ["driver"],
}


def get_keywords(query):
    q = query.lower().strip()
    if q in ROLE_TO_KEYWORDS:
        return ROLE_TO_KEYWORDS[q]
    words = q.split()
    if not words:
        return [q]
    stop_words = {"senior", "junior", "middle", "lead", "head", "of", "the"}
    clean_words = [w for w in words if w not in stop_words]
    return [clean_words[0]] if clean_words else [words[0]]


def fetch_jooble(query):
    try:
        api_key = st.secrets["JOOBLE_API_KEY"]
    except Exception:
        print("❌ NO JOOBLE KEY")
        return []

    url = f"https://jooble.org/api/{api_key}"
    jobs = []
    seen_links = set()
    keywords_list = get_keywords(query)

    for kw in keywords_list:
        try:
            payload = {"keywords": kw, "location": "", "resultonpage": 20}
            response = requests.post(url, json=payload, timeout=20)
            print(f"JOOBLE: {kw} → {response.status_code}")
            if response.status_code != 200:
                continue
            data = response.json()
            print("JOOBLE total:", data.get("totalCount"))
            for job in data.get("jobs", []):
                link = job.get("link", "")
                title = job.get("title", "").strip()
                if not title or not link or link in seen_links:
                    continue
                seen_links.add(link)
                jobs.append({
                    "title": title,
                    "company": job.get("company", "").strip(),
                    "location": job.get("location", "") or "Не вказано",
                    "link": link,
                    "description": job.get("snippet", "")[:300],
                    "source": "Jooble",
                    "salary": job.get("salary", "")
                })
        except Exception as e:
            print("Jooble inner error:", e)

    return jobs


def search_jooble_jobs(query, city="Київ"):
    from geo_filter import sort_by_city
    jobs = fetch_jooble(query)
    if not jobs and query.lower() != "job":
        print("⚠️ fallback → job")
        jobs = fetch_jooble("job")
    return sort_by_city(jobs, city)[:30]


# =========================
# FILTER HELPERS (для сумісності)
# =========================
def normalize_text(value):
    return (value or "").lower().strip()


def get_job_text(job):
    return normalize_text(
        job.get("title", "") + " " +
        job.get("location", "") + " " +
        job.get("description", "")
    )


def is_relevant_job(job, profile):
    text = get_job_text(job)
    roles = [r.lower() for r in profile.get("roles", [])]
    skills = [s.lower() for s in profile.get("skills", [])]
    return any(r in text for r in roles) or any(s in text for s in skills)


def is_level_match(job, profile):
    text = get_job_text(job)
    level = normalize_text(profile.get("level", ""))
    if level == "senior" and any(w in text for w in ["junior", "trainee", "intern"]):
        return False
    if level == "junior" and any(w in text for w in ["senior", "lead", "head"]):
        return False
    return True


def filter_by_preferences(job, preferences):
    text = get_job_text(job)
    if preferences.get("remote") == "Віддалено":
        if "remote" not in text and "віддалено" not in text:
            return False
    if preferences.get("english") in ["A1-A2", "B1"]:
        if "english" in text:
            return False
    return True
