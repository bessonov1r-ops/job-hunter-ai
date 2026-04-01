import requests
import streamlit as st


def is_valid_job_link(link):
    return any([
        "work.ua/jobs/" in link,
        "robota.ua" in link,
        "dou.ua/vacancies/" in link
    ])


def search_google_jobs(query, city="Київ"):
    jobs = []
    try:
        api_key = st.secrets["SERP_API_KEY"]
    except Exception:
        api_key = "85ed719fe945ed36c40116ce47f78e367033cc151fe9d0a0fcf12a1304cd2705"

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": f"{query} {city} вакансія site:work.ua/jobs OR site:robota.ua OR site:dou.ua/vacancies",
        "hl": "uk",
        "gl": "ua",
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if "organic_results" not in data:
            return []

        for job in data["organic_results"]:
            link = job.get("link", "")
            if not is_valid_job_link(link):
                continue
            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("source", ""),
                "location": city,
                "link": link,
                "description": job.get("snippet", ""),
                "source": "Google"
            })
    except Exception as e:
        print(f"Google error: {e}")

    return jobs
    
