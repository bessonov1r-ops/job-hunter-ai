import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.work.ua"


class Job:
    def __init__(self, title, company, city, url, salary=""):
        self.title = title
        self.company = company
        self.city = city
        self.url = url
        self.salary = salary


def is_valid_job_link(href):
    return href and re.match(r"^/jobs/\d+/?$", href)


def get_workua_jobs(query="designer", city="kyiv"):
    url = f"{BASE_URL}/jobs-{city}-{query}/"

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    seen = set()

    cards = soup.select("div.card")

    for card in cards:

        # 🔥 ВАЖЛИВО: шукаємо ВСІ <a> всередині карточки
        links = card.find_all("a", href=True)

        job_link = None
        title = ""

        for a in links:
            href = a["href"]

            # беремо тільки /jobs/ID
            if is_valid_job_link(href):
                job_link = href
                title = a.get_text(strip=True)
                break

        if not job_link:
            continue

        if job_link in seen:
            continue

        seen.add(job_link)

        full_url = BASE_URL + job_link

        company_tag = card.select_one("a.company")
        company = company_tag.text.strip() if company_tag else ""

        city_tag = card.select_one("span.text-muted")
        city_name = city_tag.text.strip() if city_tag else ""

        salary_tag = card.select_one("span.salary")
        salary = salary_tag.text.strip() if salary_tag else ""

        jobs.append(Job(title, company, city_name, full_url, salary))

    print("WORK.UA LINKS:")
    for j in jobs[:5]:
        print(j.url)

    return jobs[:5]