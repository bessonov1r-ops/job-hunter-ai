
import requests
import xml.etree.ElementTree as ET
import re


def search_dou_jobs(query):
    jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://jobs.dou.ua/vacancies/feeds/"
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        channel = root.find("channel")
        if channel is None:
            return jobs

        # Унікальні слова запиту довжиною > 2
        query_words = list(set([
            w.strip()
            for w in query.lower().split()
            if len(w) > 2
        ]))

        for item in channel.findall("item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = re.sub(r"<[^>]+>", "", item.findtext("description", "")).strip()
            company = item.findtext("author", "DOU").strip() or "DOU"
            full_text = (title + " " + desc).lower()

            # Match score
            score = sum(1 for w in query_words if w in full_text)
            if score < 1:
                continue

            jobs.append({
                "title": title.title(),
                "company": company,
                "location": "Україна",
                "link": link,
                "description": desc[:300],
                "source": "DOU",
                "score": score
            })

        # Сортуємо по match
        jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)

    except Exception as e:
        print(f"DOU error: {e}")

    return jobs
