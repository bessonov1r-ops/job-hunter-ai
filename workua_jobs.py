import requests
from bs4 import BeautifulSoup


def search_workua_jobs(query, city="Київ"):
    jobs = []

    # 🔥 нормалізація міста (важливо для URL)
    city_slug = city.lower().replace(" ", "-")

    # 🔥 формуємо URL
    url = f"https://www.work.ua/jobs-{city_slug}-{query.replace(' ', '+')}/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            print("Work.ua status:", response.status_code)
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # 🔥 ключовий блок вакансій
        vacancies = soup.find_all("div", class_="card")

        for v in vacancies[:20]:

            title_tag = v.find("h2")
            link_tag = v.find("a", href=True)
            company_tag = v.find("div", class_="add-top-xs")
            location_tag = v.find("span", class_="text-muted")

            title = title_tag.text.strip() if title_tag else ""
            link = "https://www.work.ua" + link_tag["href"] if link_tag else ""
            company = company_tag.text.strip() if company_tag else ""
            location = location_tag.text.strip() if location_tag else city

            if title and link:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link,
                    "description": "",
                    "source": "Work.ua"
                })

    except Exception as e:
        print("Work.ua error:", e)

    return jobs
