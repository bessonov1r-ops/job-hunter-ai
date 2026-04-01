import requests
from bs4 import BeautifulSoup

def search_workua(query="sales"):
    url = f"https://www.work.ua/jobs-kyiv-{query}/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []

    cards = soup.find_all("div", class_="card")

    for card in cards:
        try:
            title_tag = card.find("h2")

            title = title_tag.text.strip()
            link = "https://www.work.ua" + title_tag.find("a")["href"]

            company = card.find("a", class_="company").text.strip() if card.find("a", class_="company") else "—"

            jobs.append({
                "title": title,
                "company": company,
                "location": "Київ",
                "link": link,
                "description": title
            })

        except:
            continue

    return jobs
