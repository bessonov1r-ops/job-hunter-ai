import requests
from bs4 import BeautifulSoup

def search_dou_jobs():
    jobs = []

    url = "https://jobs.dou.ua/vacancies/?search="

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select("li.l-vacancy"):
            title = item.select_one("a.vt")
            company = item.select_one(".company")
            city = item.select_one(".cities")

            if not title:
                continue

            jobs.append({
                "title": title.text.strip(),
                "company": company.text.strip() if company else "",
                "location": city.text.strip() if city else "",
                "link": title["href"],
                "description": "",
                "source": "DOU"
            })

    except Exception as e:
        print("DOU error:", e)

    return jobs
    
