import requests
import streamlit as st


def search_serp_jobs(query, city="Київ"):
    jobs = []

    try:
        api_key = st.secrets["SERPAPI_KEY"]
        print("SERP KEY:", api_key[:5])
        print("SERP KEY OK:", bool(api_key))
    except Exception:
        print("❌ NO SERPAPI KEY")
        return []

    queries = [
        f"{query} {city} site:work.ua",
        f"{query} {city} site:rabota.ua",
        f"{query} {city} site:linkedin.com/jobs"
    ]

    for q in queries:
        try:
            print("SERP QUERY:", q)

            params = {
                "engine": "google",
                "q": q,
                "api_key": api_key,
                "num": 10
            }

            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=20
            )

            print("SERP STATUS:", response.status_code)

            if response.status_code != 200:
                continue

            data = response.json()

            for result in data.get("organic_results", []):
                link  = result.get("link", "")
                title = result.get("title", "")

                if not link or not title:
                    continue

                # Company extraction — priority: displayed_link › chain → source
                raw_company = result.get("displayed_link", "") or result.get("source", "") or ""

                if "›" in raw_company:
                    # "work.ua › Sales › TechCorp" → take last segment
                    company = raw_company.split("›")[-1].strip()
                else:
                    company = raw_company.strip()

                # Reject values that look like domains or URL slugs (noise)
                _noise = {
                    "work.ua", "rabota.ua", "robota.ua", "djinni.co",
                    "linkedin.com", "hh.ua", "dou.ua", "jooble.org",
                    "jobs", "vacancy", "vacancies", "career", "careers",
                }
                if not company or company.lower() in _noise or "." in company and "/" not in company and len(company) < 20:
                    company = "—"

                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    city,
                    "link":        link,
                    "description": result.get("snippet", ""),
                    "source":      "SerpAPI",
                })

        except Exception as e:
            print("SerpAPI error:", e)

    print("SERP TOTAL JOBS:", len(jobs))
    return jobs