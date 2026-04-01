import requests
import xml.etree.ElementTree as ET
import re

_RSS_URL = "https://djinni.co/jobs/rss/"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_TIMEOUT = 12


def get_djinni_jobs(query: str) -> list:
    if not query or not query.strip():
        return []

    try:
        resp = requests.get(
            _RSS_URL,
            params={"search": query},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
    except requests.RequestException as e:
        print(f"Djinni request error: {e}")
        return []

    if resp.status_code != 200:
        print(f"Djinni HTTP {resp.status_code}")
        return []

    # Use resp.content (bytes) — ET.fromstring handles encoding declaration correctly
    # resp.text (str) + encoding="utf-8" declaration = XML parse error
    jobs = _parse_rss(resp.content)
    print(f"DJINNI RAW: {len(jobs)}")
    return jobs


def _parse_rss(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"Djinni RSS parse error: {e}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    return [j for j in (_parse_item(i) for i in channel.findall("item")) if j]


def _parse_item(item):
    try:
        title_raw = item.findtext("title", "").strip()
        link      = item.findtext("link",  "").strip()
        desc_raw  = item.findtext("description", "").strip()
        author    = item.findtext("author", "").strip()

        if not title_raw or not link:
            return None

        # RSS title format: "Job Title at Company Name"
        if " at " in title_raw:
            title, company = title_raw.rsplit(" at ", 1)
        else:
            title   = title_raw
            company = author or "—"   # author tag has company name in Djinni RSS

        description = re.sub(r"<[^>]+>", " ", desc_raw).strip()

        return {
            "title":       title.strip(),
            "company":     company.strip(),
            "description": description,
            "link":        link,
            "source":      "Djinni",
        }
    except Exception:
        return None