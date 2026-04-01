def analyze_candidate(text):
    text = text.lower()

    skills = []
    roles = []
    level = "unknown"

    # skills
    if "b2b" in text:
        skills.append("B2B Sales")

    if "crm" in text:
        skills.append("CRM")

    if "saas" in text:
        skills.append("SaaS")

    # roles
    if "sales" in text:
        roles.append("Sales Manager")

    if "account" in text:
        roles.append("Account Manager")

    if "business development" in text:
        roles.append("BDM")

    # level
    if "5" in text or "6" in text or "7" in text:
        level = "Middle+"

    return {
        "skills": skills,
        "roles": roles,
        "level": level
    }
