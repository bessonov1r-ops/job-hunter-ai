import re


# =========================
# ROLE ALIASES — Ukrainian/informal → standard English roles
# =========================
ROLE_ALIASES = {
    # Ukrainian exact words → English roles
    "повар":       ["Cook", "Chef"],
    "кухар":       ["Cook", "Chef"],
    "кондитер":    ["Pastry Chef", "Baker"],
    "водій":       ["Driver"],
    "логіст":      ["Logistics Manager"],
    "бухгалтер":   ["Accountant"],
    "рекрутер":    ["Recruiter"],
    "програміст":  ["Software Developer"],
    "розробник":   ["Software Developer"],
    "маркетолог":  ["Marketing Manager"],
    "продажник":   ["Sales Manager"],
    "сейлз":       ["Sales Manager"],
    "фотограф":    ["Photographer"],
    "дизайнер":    ["Designer"],
    "вчитель":     ["Teacher"],
    "викладач":    ["Teacher"],
    "юрист":       ["Lawyer"],
    "лікар":       ["Doctor"],
    # "менеджер" intentionally removed — too generic, triggers on unrelated text
    # e.g. "я менеджер по роботі" should not produce "Manager" as a search role
    # Ukrainian stems (partial words — cover different word forms)
    # photographer / photography related
    "зйомк":       ["Photographer"],   # зйомка, зйомку, зйомкою
    "зніма":       ["Photographer"],   # знімаю, знімати, знімання
    "фотозйом":    ["Photographer"],
    # cook related
    "кухн":        ["Cook"],           # кухня, кухні, кухнею
    "готу":        ["Cook"],           # готую, готувати, готування
    "шеф":         ["Chef"],
    # driver / delivery related
    "доставк":     ["Driver"],         # доставка, доставки, доставкою
    "кур'єр":      ["Driver"],
    "курєр":       ["Driver"],         # without apostrophe variant
    # sales related stems
    "продаж":      ["Sales Manager"],  # продажі, продажів, продажах
    # design
    "дизайн":      ["Designer"],
    # medical
    "медсестр":    ["Nurse"],
    "фельдшер":    ["Paramedic"],
    # beauty
    "перукар":     ["Hairdresser"],
    "стиліст":     ["Stylist"],
    # construction / trade
    "зварювальник": ["Welder"],
    "механік":     ["Mechanic"],
    "електрик":    ["Electrician"],
    "будівельник": ["Construction Worker"],
    # architecture
    "архітектор":  ["Architect"],
    # gamedev
    "геймдев":     ["Game Designer", "Game Developer"],
    "ігровий":     ["Game Designer"],
}

# Direct keyword → role mapping (English + Ukrainian word fragments)
# Used by detect_roles for fast, comprehensive role extraction
_ROLE_KEYWORDS = {
    # Sales
    "sales manager":           "Sales Manager",
    "account manager":         "Account Manager",
    "business development":    "Business Development Manager",
    "customer success":        "Customer Success Manager",
    "key account":             "Key Account Manager",
    "sales executive":         "Sales Executive",
    "account executive":       "Account Executive",
    # Food
    "photographer":            "Photographer",
    "photography":             "Photographer",
    "cook":                    "Cook",
    "chef":                    "Chef",
    "baker":                   "Baker",
    "pastry chef":             "Pastry Chef",
    # Transport
    "driver":                  "Driver",
    "delivery driver":         "Driver",
    "truck driver":            "Driver",
    "courier":                 "Driver",
    # IT
    "developer":               "Software Developer",
    "software engineer":       "Software Developer",
    "frontend developer":      "Frontend Developer",
    "backend developer":       "Backend Developer",
    "devops":                  "DevOps Engineer",
    "qa engineer":             "QA Engineer",
    "data scientist":          "Data Scientist",
    "data analyst":            "Data Analyst",
    "ml engineer":             "ML Engineer",
    # Marketing
    "marketing manager":       "Marketing Manager",
    "smm manager":             "SMM Manager",
    "seo specialist":          "SEO Specialist",
    "content manager":         "Content Manager",
    # HR
    "recruiter":               "Recruiter",
    "hr manager":              "HR Manager",
    "talent acquisition":      "Recruiter",
    # Finance / Ops
    "accountant":              "Accountant",
    "logistics manager":       "Logistics Manager",
    "supply chain":            "Logistics Manager",
    "project manager":         "Project Manager",
    "product manager":         "Product Manager",
    # Design
    "designer":                "Designer",
    "ui/ux":                   "UI/UX Designer",
    "graphic designer":        "Graphic Designer",
    # Gamedev
    "game designer":           "Game Designer",
    "level designer":          "Level Designer",
    "game developer":          "Game Developer",
    "game design":             "Game Designer",
    "level design":            "Level Designer",
    "unity developer":         "Game Developer",
    "unreal developer":        "Game Developer",
    # Education / Legal / Medical
    "teacher":                 "Teacher",
    "lawyer":                  "Lawyer",
    "doctor":                  "Doctor",
    "nurse":                   "Nurse",
}


# =========================
# DOMAIN MAP (розширений)
# =========================
DOMAIN_MAP = {
    "sales": {
        "keywords": ["sales", "продаж", "account", "b2b", "b2c", "business development", "client"],
        "roles": ["Sales Manager", "Account Manager", "Business Development Manager"],
    },
    "it": {
        "keywords": ["python", "javascript", "developer", "frontend", "backend", "qa", "devops"],
        "roles": ["Python Developer", "Frontend Developer", "DevOps Engineer"],
    },
    "marketing": {
        "keywords": ["marketing", "smm", "seo", "content", "performance"],
        "roles": ["Marketing Manager", "SMM Manager"],
    },
    "logistics": {
        "keywords": ["logistics", "supply", "warehouse", "склад", "логіст"],
        "roles": ["Логіст"],
    },
    "finance": {
        "keywords": ["accountant", "finance", "financial", "бухгалтер"],
        "roles": ["Бухгалтер"],
    },
    "hr": {
        "keywords": ["hr", "recruiter", "talent"],
        "roles": ["HR Manager", "Recruiter"],
    },
    "gamedev": {
        "keywords": ["game", "level design", "match-3", "unity", "unreal", "game designer",
                     "level designer", "game mechanics", "gamedev", "gameplay"],
        "roles": ["Game Designer", "Level Designer", "Game Developer"],
    },
}


# =========================
# ГЛОБАЛЬНИЙ СЛОВНИК СКІЛІВ (20+)
# =========================
SKILL_DB = {
    # sales
    "crm": "CRM",
    "pipeline": "Pipeline",
    "lead generation": "Lead Generation",
    "closing": "Closing",
    "upsell": "Upsell",
    "cross-sell": "Cross-sell",
    "retention": "Retention",
    "negotiation": "Negotiation",
    "переговор": "Negotiation",
    "sales": "Sales",
    "b2b": "B2B",
    "b2c": "B2C",

    # management
    "management": "Management",
    "управл": "Management",
    "team": "Team Management",
    "leadership": "Leadership",

    # analytics
    "analytics": "Analytics",
    "excel": "Excel",
    "sql": "SQL",
    "power bi": "Power BI",

    # IT
    "python": "Python",
    "javascript": "JavaScript",
    "react": "React",
    "docker": "Docker",
    "aws": "AWS",

    # marketing
    "seo": "SEO",
    "smm": "SMM",
    "ads": "Ads",
    "google ads": "Google Ads",

    # soft skills
    "communication": "Communication",
    "комунікац": "Communication",
    "problem solving": "Problem Solving",
}


# =========================
# ВИТЯГУВАННЯ СКІЛІВ (🔥 НОВЕ)
# =========================
def extract_skills(text):
    skills = set()

    for key, label in SKILL_DB.items():
        if key in text:
            skills.add(label)

    # 🔥 fallback — витягуємо слова після "skills:"
    skill_block = re.findall(r"(skills|навички)[:\-](.*)", text)
    if skill_block:
        raw = skill_block[0][1]
        for word in raw.split(","):
            if len(word.strip()) > 2:
                skills.add(word.strip().title())

    return list(skills)[:20]  # 🔥 до 20 скілів


# =========================
# EXPERIENCE (FIXED)
# =========================
def extract_experience(text):
    exp = 0

    plus_match = re.search(r'(\d+)\s*\+', text)
    if plus_match:
        exp = int(plus_match.group(1))

    exp_match = re.search(r'(\d+)\s*(?:рок|роки|years|year)', text)
    if exp_match:
        exp = max(exp, int(exp_match.group(1)))

    if "10+" in text:
        exp = max(exp, 10)

    return exp


# =========================
# DOMAIN DETECTION
# =========================
def detect_domains(text):
    domains = []

    for d, data in DOMAIN_MAP.items():
        if any(k in text for k in data["keywords"]):
            domains.append(d)

    return domains


# =========================
# ROLE EXPANSION — skill/domain → adjacent roles
# Each rule: if ANY of the trigger keywords appear in text → add the role
# Rules are ordered by specificity; roles are deduplicated and capped at 5 total
# =========================
ROLE_EXPANSION_RULES = [

    # --- SALES domain ---
    {
        "triggers": ["retention", "upsell", "cross-sell", "customer success", "churn"],
        "role": "Customer Success Manager",
        "require_domain": "sales",
    },
    {
        "triggers": ["key account", "key accounts", "strategic account", "enterprise"],
        "role": "Key Account Manager",
        "require_domain": "sales",
    },
    {
        "triggers": ["cold call", "холодні дзвінки", "outbound", "lead generation", "prospecting"],
        "role": "Sales Development Representative",
        "require_domain": "sales",
    },
    {
        "triggers": ["saas", "software sales", "tech sales", "it sales"],
        "role": "Account Executive",
        "require_domain": "sales",
    },
    {
        "triggers": ["partnership", "партнерства", "channel sales", "affiliate"],
        "role": "Partnership Manager",
        "require_domain": "sales",
    },

    # --- IT domain ---
    {
        "triggers": ["team lead", "tech lead", "leading team", "engineering manager"],
        "role": "Engineering Manager",
        "require_domain": "it",
    },
    {
        "triggers": ["aws", "azure", "gcp", "kubernetes", "infrastructure"],
        "role": "DevOps Engineer",
        "require_domain": "it",
    },
    {
        "triggers": ["react", "vue", "angular", "frontend", "ui"],
        "role": "Frontend Developer",
        "require_domain": "it",
    },
    {
        "triggers": ["django", "fastapi", "flask", "backend", "rest api", "node"],
        "role": "Backend Developer",
        "require_domain": "it",
    },
    {
        "triggers": ["ml", "machine learning", "deep learning", "ai model", "llm"],
        "role": "ML Engineer",
        "require_domain": "it",
    },
    {
        "triggers": ["qa", "testing", "test automation", "selenium", "cypress"],
        "role": "QA Engineer",
        "require_domain": "it",
    },

    # --- MARKETING domain ---
    {
        "triggers": ["performance", "google ads", "facebook ads", "paid traffic", "ppc"],
        "role": "Performance Marketing Manager",
        "require_domain": "marketing",
    },
    {
        "triggers": ["seo", "organic", "content marketing"],
        "role": "SEO Specialist",
        "require_domain": "marketing",
    },
    {
        "triggers": ["brand", "брендинг", "brand manager"],
        "role": "Brand Manager",
        "require_domain": "marketing",
    },

    # --- HR domain ---
    {
        "triggers": ["sourcing", "headhunting", "linkedin recruiter", "talent acquisition"],
        "role": "Talent Acquisition Specialist",
        "require_domain": "hr",
    },
    {
        "triggers": ["onboarding", "people ops", "hr business partner", "hrbp"],
        "role": "HR Business Partner",
        "require_domain": "hr",
    },

    # --- LOGISTICS domain ---
    {
        "triggers": ["supply chain", "procurement", "warehouse", "inventory"],
        "role": "Supply Chain Manager",
        "require_domain": "logistics",
    },
]


def expand_roles_from_skills(roles, text, domains):
    """
    Infer adjacent roles based on skills and domain signals in text.
    Adds at most enough roles to reach 5 total — never explodes the list.
    Only adds a role if its required domain matches detected domains.
    """
    expanded = list(roles)  # copy to avoid mutating original

    for rule in ROLE_EXPANSION_RULES:
        # Stop once we have 5 roles
        if len(expanded) >= 5:
            break

        # Skip if role already present (case-insensitive)
        role = rule["role"]
        if any(role.lower() == r.lower() for r in expanded):
            continue

        # Domain gate — only add if relevant domain detected
        required_domain = rule.get("require_domain")
        if required_domain and required_domain not in domains:
            continue

        # Trigger match — any keyword in text
        if any(trigger in text for trigger in rule["triggers"]):
            expanded.append(role)

    return expanded[:5]


# =========================
# ROLE DETECTION
# =========================
def detect_roles(text, domains):
    roles = []
    seen  = set()

    # 1. Direct keyword match — longest phrase first (prevents short words shadowing longer ones)
    sorted_kw = sorted(_ROLE_KEYWORDS.keys(), key=len, reverse=True)
    for kw in sorted_kw:
        if kw in text:
            role = _ROLE_KEYWORDS[kw]
            if role not in seen:
                roles.append(role)
                seen.add(role)

    # 2. Ukrainian aliases + stems (partial word matching)
    for alias, alias_roles in ROLE_ALIASES.items():
        if alias in text:
            for role in alias_roles:
                if role not in seen:
                    roles.append(role)
                    seen.add(role)

    # 3. Domain fallback — only if nothing detected above
    if not roles:
        for d in domains:
            for role in DOMAIN_MAP[d]["roles"]:
                if role not in seen:
                    roles.append(role)
                    seen.add(role)

    # 4. HARD FALLBACK — roles must never be empty
    # Extract first meaningful word from text as a last resort role label
    # This ensures search always has something to work with
    if not roles:
        words = [w for w in text.split() if len(w) > 3 and w.isalpha()]
        if words:
            # Use first long word, capitalized — better than nothing
            roles = [words[0].capitalize()]

    return roles[:5]


# =========================
# AI RESUME PARSER
# =========================
def ai_parse_resume(text):
    """
    Parse resume/description using Claude AI.
    Returns dict with role, skills, level, domains.
    Falls back to static logic if AI unavailable.
    """
    import json
    try:
        from ai_agent import ask_ai
    except ImportError:
        return None

    prompt = f"""Parse this resume or job description and return ONLY a JSON object.
No explanation, no markdown, no backticks — raw JSON only.

Text: {text[:2000]}

Return this exact structure:
{{
  "roles": ["Primary Role", "Secondary Role"],
  "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "level": "junior|middle|senior",
  "experience_years": 0,
  "domains": ["domain1"]
}}

Rules:
- roles: 1-3 most relevant job titles in English (e.g. ["Game Designer", "Level Designer"])
- skills: 5-12 concrete skills — tools, technologies, methods (e.g. Unity, Level Design, CRM, Python)
- level: junior (0-1 yr), middle (2-4 yr), senior (5+ yr)
- experience_years: integer total years, 0 if unknown
- domains: 1-2 from: sales, it, marketing, logistics, finance, hr, gamedev, design, education, other
- For gamedev resumes use domain "gamedev" and extract game-specific roles and tools"""

    system = "You are a resume parser. Return only valid JSON, nothing else."

    try:
        raw = ask_ai(prompt, system=system)
        if not raw or raw.startswith("❌"):
            return None
        # Strip any accidental markdown
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return data
    except Exception as e:
        print(f"AI parse error: {e}")
        return None


# =========================
# MAIN ANALYZE
# =========================
def analyze_candidate(text, extra=None):
    t = (text or "").strip()
    if extra:
        t += " " + " ".join(str(v) for v in extra.values())

    # ── Try AI parsing first ──
    ai = ai_parse_resume(t)

    if ai and (ai.get("roles") or ai.get("role")):
        # Support both "roles" array (new) and "role" string (legacy)
        raw_roles = ai.get("roles") or []
        if not raw_roles and ai.get("role"):
            raw_roles = [ai["role"]] if isinstance(ai["role"], str) else ai["role"]
        roles   = [r for r in raw_roles if r and str(r).strip()][:3]
        skills  = [s for s in ai.get("skills", []) if s and str(s).strip()][:12]
        level   = ai.get("level", "junior")
        exp     = int(ai.get("experience_years") or 0)
        domains = ai.get("domains", [])
        if level not in ("junior", "middle", "senior"):
            level = "senior" if exp >= 5 else "middle" if exp >= 2 else "junior"
        if roles:
            return {
                "domains": domains,
                "skills":  skills,
                "roles":   roles,
                "level":   level,
                "experience_years": exp,
            }

    # ── Fallback: static rule-based logic ──
    tl = t.lower()
    if extra:
        tl += " " + " ".join(str(v).lower() for v in extra.values())

    domains = detect_domains(tl)
    skills  = extract_skills(tl)
    roles   = detect_roles(tl, domains)
    roles   = expand_roles_from_skills(roles, tl, domains)
    exp     = extract_experience(tl)
    level   = "senior" if exp >= 5 else "middle" if exp >= 2 else "junior"

    return {
        "domains": domains,
        "skills":  skills,
        "roles":   roles,
        "level":   level,
        "experience_years": exp,
    }


# =========================
# CLARIFICATION
# =========================
def score_confidence(profile):
    score = 0.0
    if profile.get("roles"):        score += 0.5
    if len(profile.get("skills", [])) >= 2: score += 0.3
    if profile.get("experience_years", 0) > 0: score += 0.2
    return round(min(score, 1.0), 2)


def needs_clarification(profile):
    questions = []
    confidence = profile.get("confidence", score_confidence(profile))

    # Ask about role ONLY if roles are missing
    if not profile.get("roles"):
        questions.append({
            "key": "sphere",
            "question": "🎯 Яку посаду шукаєш?",
            "options": [
                "🔍 Шукати у всіх сферах",
                "Sales Manager",
                "Developer",
                "Marketing",
                "Logistics",
                "Cook / Chef",
                "Driver",
                "Інше (введу сам)",
            ]
        })

    if profile.get("experience_years", 0) == 0:
        questions.append({
            "key": "experience",
            "question": "📅 Скільки років досвіду?",
            "options": ["1-2", "3-5", "5-10", "10+"]
        })

    questions.append({
        "key": "remote",
        "question": "🏠 Формат роботи?",
        "options": ["Офіс", "Віддалено", "Гібрид", "Не важливо"]
    })

    questions.append({
        "key": "salary",
        "question": "💰 Очікувана зарплата?",
        "options": ["<1000$", "1000-2000$", "2000-4000$", "4000$+"]
    })

    questions.append({
        "key": "english",
        "question": "🌍 Рівень англійської?",
        "options": ["A1-A2", "B1", "B2", "C1+"]
    })

    return questions


# =========================
# MERGE PROFILE — resume + clarification answers
# =========================
def merge_profile(profile, answers):
    p = profile.copy()
    p["preferences"] = profile.get("preferences", {}).copy()

    if answers.get("sphere"):
        sphere = answers["sphere"].strip()

        if sphere.startswith("🔍"):
            p["roles"] = []
            p["search_mode"] = "broad"

        elif "інше" in sphere.lower():
            p["roles"] = []
            p["search_mode"] = "unknown"

        else:
            sphere_lower = sphere.lower()
            normalized = []

            for alias, alias_roles in ROLE_ALIASES.items():
                if alias in sphere_lower:
                    normalized = alias_roles
                    break

            if not normalized:
                sphere_map = {
                    "sales manager":        ["Sales Manager"],
                    "developer":            ["Software Developer"],
                    "marketing":            ["Marketing Manager"],
                    "logistics":            ["Logistics Manager"],
                    "finance / accountant": ["Accountant"],
                    "hr":                   ["HR Manager", "Recruiter"],
                    "cook / chef":          ["Cook", "Chef"],
                    "driver":               ["Driver"],
                }
                normalized = sphere_map.get(sphere_lower, [])

            if normalized:
                p["roles"] = normalized
                p.pop("search_mode", None)

    if answers.get("experience"):
        exp_map = {"1-2": 1, "3-5": 3, "5-10": 6, "10+": 10}
        exp = exp_map.get(answers["experience"], p.get("experience_years", 0))
        p["experience_years"] = exp
        p["level"] = "senior" if exp >= 5 else "middle" if exp >= 2 else "junior"

    if answers.get("remote"):
        p["preferences"]["remote"] = answers["remote"]
    if answers.get("salary"):
        p["preferences"]["salary"] = answers["salary"]
    if answers.get("english"):
        p["preferences"]["english"] = answers["english"]

    p["confidence"] = score_confidence(p)
    return p


# =========================
# STRATEGY
# =========================
def generate_strategy(profile):
    return {
        "go_for": profile.get("roles", []),
        "avoid": [],
        "salary_range": "залежить від рівня"
    }