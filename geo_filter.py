CITY_MAP = {
    "київ":    ["kyiv", "kiev", "київ"],
    "львів":   ["lviv", "львів"],
    "дніпро":  ["dnipro", "дніпро"],
    "одеса":   ["odesa", "odessa", "одеса"],
    "харків":  ["kharkiv", "харків"],
    "варшава": ["warsaw", "варшава", "warszawa"],
}


def get_city_score(job, city):
    if not city or "не важливо" in city.lower():
        return 1

    city_lower = city.lower().strip()
    text = (
        job.get("title", "") + " " +
        job.get("location", "") + " " +
        job.get("description", "")
    ).lower()

    variants = CITY_MAP.get(city_lower, [city_lower])

    # Точне місто
    if any(v in text for v in variants):
        return 3

    # Remote
    if any(x in text for x in ["remote", "віддалено", "дистанційн"]):
        return 2

    return 0


def sort_by_city(jobs, city):
    return sorted(
        jobs,
        key=lambda job: get_city_score(job, city),
        reverse=True
    )


def is_relevant_city(job, city):
    return get_city_score(job, city) > 0
