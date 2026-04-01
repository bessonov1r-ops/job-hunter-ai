import re

def extract_salary(text):
    if not text:
        return None

    text = text.lower()

    usd = re.findall(r'(\d{3,5})\s*\$|\$(\d{3,5})|(\d{3,5})\s*usd', text)
    uah = re.findall(r'(\d{4,6})\s*грн', text)

    salaries = []

    for group in usd:
        for val in group:
            if val:
                salaries.append(int(val))

    for val in uah:
        salaries.append(int(val) / 40)

    if not salaries:
        return None

    return max(salaries)