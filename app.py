import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "sources"))

import streamlit as st
from brain import analyze_candidate, needs_clarification, merge_profile
from geo_filter import sort_by_city, is_relevant_city
from aggregator import collect_jobs
from filter_jobs import filter_jobs_pipeline, has_role_match, skill_matches, ROLE_SHORT_NAMES, ROLE_CLUSTERS
from ai_agent import ask_ai
from ai_score import smart_score

st.set_page_config(page_title="Besson AI Hunter", layout="wide")

# ============================================================
# DESIGN SYSTEM — dark SaaS theme
# ============================================================
st.markdown("""
<style>
/* ── BASE ── */
html,body,.stApp { background:#0f172a !important; color:#e5e7eb !important; }

/* ── INPUTS ── */
.stTextArea textarea,
.stTextInput input {
    background:#1e293b !important; color:#e5e7eb !important;
    border:1px solid #334155 !important; border-radius:8px !important;
}
.stTextArea textarea:focus,.stTextInput input:focus {
    border-color:#6366f1 !important; outline:none !important;
}
.stTextArea textarea::placeholder,.stTextInput input::placeholder { color:#475569 !important; }
.stTextInput label,.stTextArea label,.stSelectbox label { color:#94a3b8 !important; font-size:13px !important; }

/* ── SELECTBOX ── */
[data-baseweb="select"]>div,
[data-baseweb="select"] div[class*="ValueContainer"],
[data-baseweb="popover"] ul,[data-baseweb="menu"] {
    background:#1e293b !important; color:#e5e7eb !important; border-color:#334155 !important;
}
[data-baseweb="select"] svg { fill:#94a3b8 !important; }

/* ── CARD ── */
.s-card {
    background:#1e293b; border:1px solid #334155;
    border-radius:12px; padding:20px 24px; margin-bottom:16px;
    transition:border-color .2s;
}
.s-card:hover { border-color:#6366f1; }

/* ── SECTION HEADER ── */
.sec-header {
    font-size:12px; font-weight:700; color:#64748b;
    text-transform:uppercase; letter-spacing:.08em; margin:0 0 8px 0;
}

/* ── ALL BUTTONS — chip style ── */
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-primary"] {
    border-radius:16px !important;
    font-size:12px !important;
    padding:4px 12px !important;
    min-height:28px !important;
    height:auto !important;
    line-height:1.3 !important;
    box-shadow:none !important;
    white-space:nowrap !important;
    width:auto !important;
    transition:border-color .15s, opacity .15s !important;
}
button[data-testid^="stBaseButton"]:active {
    transform:none !important; box-shadow:none !important;
}

/* ── SUGGESTION BUTTONS — dashed, faded ── */
button[data-testid="stBaseButton-secondary"][title^="+"],
button[data-testid="stBaseButton-secondary"][title^="Додати"] {
    opacity:.65 !important; border-style:dashed !important;
}
button[data-testid="stBaseButton-secondary"][title^="+"]:hover,
button[data-testid="stBaseButton-secondary"][title^="Додати"]:hover {
    opacity:1 !important;
}

/* ── STATIC CHIPS (HTML) ── */
.chip {
    display:inline-flex; align-items:center; gap:5px;
    padding:4px 12px; border-radius:16px;
    font-size:12px; font-weight:500; margin:2px 3px; line-height:1.4;
    transition:opacity .15s;
}
.chip:hover { opacity:.85; cursor:pointer; }
.chip-role  { background:#1e3a5f; color:#93c5fd; border:1px solid #2563eb44; }
.chip-skill { background:#14532d; color:#86efac; border:1px solid #16a34a44; }
.chip-pref  { background:#1e1b4b; color:#a5b4fc; border:1px solid #6366f144; }
.chip-pref-active { background:#6366f1; color:white; border:1px solid #6366f1; font-weight:600; }
.chip-add   { background:transparent; color:#475569; border:1px dashed #334155; }
.chip-add:hover { color:#94a3b8; border-color:#475569; }

/* ── SPACING ── */
.stMarkdown { margin-bottom:2px !important; }
div[data-testid="stVerticalBlock"]>div { gap:4px !important; }
.stTextInput,.stTextArea,.stSelectbox { margin-bottom:6px !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background:#1e293b !important; color:#e5e7eb !important;
    border-radius:8px !important; border:1px solid #334155 !important;
}
.streamlit-expanderContent {
    background:#1e293b !important; border:1px solid #334155 !important;
    border-top:none !important; border-radius:0 0 8px 8px !important;
}

/* ── METRICS ── */
[data-testid="metric-container"] {
    background:#1e293b !important; border:1px solid #334155 !important;
    border-radius:10px !important; padding:12px 16px !important;
}
[data-testid="stMetricValue"] { color:#e5e7eb !important; }
[data-testid="stMetricLabel"] { color:#94a3b8 !important; }

/* ── MISC ── */
hr { border-color:#334155 !important; }
.stAlert { border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='color:#e5e7eb;margin-bottom:4px'>🎯 Besson AI Hunter</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#64748b;margin-top:0;margin-bottom:24px'>AI-підбір вакансій під твій профіль</p>",
            unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
for key, val in {
    "step": "input",
    "profile": None,
    "resume": "",
    "city": "Київ",
    "preferences": {},
    "applied": [],
    "skipped": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
# HELPERS
# ============================================================
def explain_match(job, profile, city):
    reasons, warnings = [], []
    text  = (job.get("title","") + " " + job.get("description","")).lower()
    title = job.get("title","").lower()
    link  = job.get("link","")
    source = job.get("source","")
    is_broad = profile.get("search_mode") == "broad" or not profile.get("roles")

    role_matched = has_role_match(job, profile)
    if role_matched and profile.get("roles"):
        short_labels = [ROLE_SHORT_NAMES.get(r, r) for r in profile["roles"]]
        reasons.append(f"🎯 Role: {' / '.join(short_labels)}")

    matched_skills = [s for s in profile.get("skills",[]) if skill_matches(s, text)]
    for s in matched_skills[:5]:
        reasons.append(f"🧠 {s}")

    if is_relevant_city(job, city):
        reasons.append(f"📍 {city}")

    level = profile.get("level","")
    if level and level.lower() in text:
        reasons.append(f"📊 {level}")

    if not role_matched and not is_broad:
        warnings.append("⚠ Інша роль")
    if len(title.strip()) < 5:
        warnings.append("⚠ Слабкий заголовок")
    if not matched_skills:
        warnings.append("⚠ Немає навичок")
    if not source or source.strip().lower() in ("","unknown"):
        warnings.append("⚠ Невідоме джерело")
    if not link or "search" in link:
        warnings.append("⚠ Підозрілий лінк")

    return reasons, warnings


def decision_hint(score, reasons, warnings):
    top = None
    if any("Role" in r or "роль" in r for r in reasons): top = "роль збігається"
    elif any(r.startswith("🧠") for r in reasons):       top = "навички збігаються"
    elif any(r.startswith("📍") for r in reasons):       top = "місто підходить"

    if score >= 70: return "✅ Хороший варіант — подавайся", "#22c55e", top
    if score >= 40: return "👀 Можливо — перевір деталі",   "#f59e0b", top
    return "⏭ Слабко — краще пропустити", "#64748b", top


def generate_cover(job, profile, style="medium"):
    role    = job.get("title","")
    company = job.get("company","")
    skills  = ", ".join(profile.get("skills",[])[:4]) or "релевантний досвід"
    years   = profile.get("experience_years", 0)
    domains = ", ".join(profile.get("domains",[])) or "своєї спеціалізації"
    level   = profile.get("level","")
    exp_str   = f"{years}+ років досвіду" if years else "досвідом у сфері"
    level_str = f" ({level})" if level and level != "unknown" else ""

    if style == "short":
        return f"Доброго дня!\n\nЗацікавила вакансія {role} у {company}.\nМаю {exp_str}{level_str}. Навички: {skills}.\nГотовий обговорити деталі.\n\nЗ повагою, [Ім'я]"
    if style == "strong":
        return f"Доброго дня, команда {company}!\n\nЯ фахівець{level_str} у сфері {domains} з {exp_str} і хочу приєднатись на позицію {role}.\n\nКомпетенції: {skills}.\n\nБуду радий поспілкуватись!\n\nЗ повагою, [Ім'я]\n[Телефон] | [Email]"
    return f"Доброго дня!\n\nМене зацікавила позиція {role} у компанії {company}.\n\nМаю {exp_str}{level_str} у напрямку {domains}.\nНавички: {skills}.\n\nБуду радий обговорити деталі.\n\nЗ повагою,\n[Твоє ім'я]"


# ============================================================
# CHIP HELPERS — pure Streamlit, no JS, no query_params
# ============================================================
def _tag_row(items, chip_class):
    """Visual-only inline chip row."""
    if not items:
        return
    html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px'>"
    for it in items:
        html += f"<span class='chip {chip_class}'>{it}</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# CHIP HELPERS — inline flow, no grid, no ✕ buttons
# ============================================================
def render_chips(items, chip_class):
    """Inline chip flow — Notion/Linear style. No grid, no buttons."""
    if not items:
        return
    html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px'>"
    for item in items:
        html += f"<span class='chip {chip_class}'>{item}</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# render_chips_removable removed — use render_chips() instead


# ============================================================
# КРОК 1 — ВВЕДЕННЯ
# ============================================================
if st.session_state.step == "input":

    st.markdown("<div class='s-card'>", unsafe_allow_html=True)
    st.markdown("<p class='sec-header'>Про себе</p>", unsafe_allow_html=True)
    resume = st.text_area(
        "",
        placeholder="Sales Manager, 3 роки B2B, CRM... або просто 'фотограф', 'кухар', 'водій'",
        height=140,
        label_visibility="collapsed",
    )
    city = st.text_input("📍 Місто пошуку", "Київ")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='s-card'>", unsafe_allow_html=True)
    st.markdown("<p class='sec-header'>Побажання</p>", unsafe_allow_html=True)
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        salary = st.selectbox("💰 Зарплата", ["Не важливо", "$1000+", "$2000+", "$3000+"])
    with pc2:
        remote = st.selectbox("🏠 Формат", ["Не важливо", "Remote", "Office", "Hybrid"])
    with pc3:
        english = st.selectbox("🇬🇧 Англійська", ["Не важливо", "B1", "B2", "C1"])
    st.markdown("</div>", unsafe_allow_html=True)


    if st.button("🔍 Знайти вакансії", type="primary", use_container_width=True):
        if not resume.strip():
            st.warning("⚠️ Введи посаду або опис: 'повар', 'водій', 'sales manager'")
            st.stop()
        profile = analyze_candidate(resume)
        st.session_state.resume  = resume
        st.session_state.city    = city
        st.session_state.profile = profile
        st.session_state.preferences = {"salary": salary, "remote": remote, "english": english}
        for k in ["jobs_cache","raw_jobs_cache","source_stats_cache","stats_cache"]:
            st.session_state.pop(k, None)

        all_q   = needs_clarification(profile)
        prefs_set = {
            "salary":  salary  != "Не важливо",
            "remote":  remote  != "Не важливо",
            "english": english != "Не важливо",
        }
        filtered_q = [q for q in all_q if not prefs_set.get(q["key"], False)]
        st.session_state.clarify_questions = filtered_q
        st.session_state.step = "clarify" if filtered_q else "results"
        st.rerun()

# ============================================================
# КРОК 2 — УТОЧНЕННЯ
# ============================================================
elif st.session_state.step == "clarify":
    profile   = st.session_state.profile
    questions = st.session_state.get("clarify_questions", [])

    if not questions:
        st.session_state.step = "results"
        st.rerun()

    st.markdown("<div class='s-card'>", unsafe_allow_html=True)
    st.markdown("<p class='sec-header'>Кілька уточнень</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8;font-size:14px;margin-bottom:16px'>Це допоможе знайти точніші вакансії</p>",
                unsafe_allow_html=True)

    with st.form("clarify_form"):
        answers = {}
        for q in questions:
            answers[q["key"]] = st.selectbox(q["question"], q["options"])

        col_a, col_b = st.columns([3, 1])
        with col_a:
            submitted = st.form_submit_button("✅ Продовжити", type="primary", use_container_width=True)
        with col_b:
            back = st.form_submit_button("← Назад", use_container_width=True)

        if submitted:
            updated = merge_profile(st.session_state.profile, answers)
            st.session_state.profile = updated
            for k in ["jobs_cache","raw_jobs_cache","source_stats_cache"]:
                st.session_state.pop(k, None)
            st.session_state.step = "results"
            st.rerun()
        if back:
            st.session_state.step = "input"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# КРОК 3 — РЕЗУЛЬТАТИ
# ============================================================
elif st.session_state.step == "results":
    profile = st.session_state.profile
    city    = st.session_state.city
    prefs   = st.session_state.get("preferences", {})

    # ---- RAW JOBS CACHE ----
    if "raw_jobs_cache" not in st.session_state:
        with st.spinner("🔍 Збираємо вакансії..."):
            raw_jobs, source_stats = collect_jobs(profile, city)
        geo = [j for j in raw_jobs if is_relevant_city(j, city)]
        if len(geo) >= 5: raw_jobs = geo

        def _norm(url):
            url = (url or "").strip().lower()
            return url.split("?")[0].rstrip("/")

        seen_l, seen_t, uniq = set(), set(), []
        for j in raw_jobs:
            nl = _norm(j.get("link",""))
            tk = (j.get("title","").lower().strip(), j.get("company","").lower().strip())
            if nl and nl in seen_l: continue
            if tk in seen_t: continue
            if nl: seen_l.add(nl)
            seen_t.add(tk)
            uniq.append(j)
        raw_jobs = sort_by_city(uniq, city)
        st.session_state.raw_jobs_cache     = raw_jobs
        st.session_state.source_stats_cache = source_stats

    # ---- SCORED JOBS CACHE ----
    if "jobs_cache" not in st.session_state:
        raw_jobs     = st.session_state.raw_jobs_cache
        source_stats = st.session_state.source_stats_cache
        try:
            filtered, filter_stats = filter_jobs_pipeline(
                raw_jobs, profile, city, prefs, source_stats=source_stats)
        except Exception as e:
            print(f"Filter error: {e}")
            filtered, filter_stats = raw_jobs, {}

        for j in filtered:
            r, w = explain_match(j, profile, city)
            sd = smart_score(j, profile, r, w, city)
            j["final_score"] = sd["score"]
            j["label"]       = sd["label"]

        jobs = sorted(filtered, key=lambda x: x.get("final_score",0), reverse=True)[:50]
        for j in jobs:
            src = j.get("source","Other")
            if isinstance(source_stats.get(src), dict):
                source_stats[src]["final"] += 1

        st.session_state.jobs_cache         = jobs
        st.session_state.filter_stats_cache = filter_stats if isinstance(filter_stats,dict) else {}

    jobs         = st.session_state.jobs_cache
    source_stats = st.session_state.source_stats_cache or {}
    filter_stats = st.session_state.get("filter_stats_cache", {})

    # ============================================================
    # Fix 8: DASHBOARD STRIP
    # ============================================================
    strong_count = len([j for j in jobs if j.get("final_score", 0) >= 70])
    medium_count = len([j for j in jobs if 40 <= j.get("final_score", 0) < 70])
    primary_role = (profile.get("roles") or ["—"])[0]
    st.markdown(
        f"<div style='background:linear-gradient(90deg,#6366f1,#8b5cf6);"
        f"padding:16px 24px;border-radius:12px;margin-bottom:20px;"
        f"display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px'>"
        f"<div style='color:white'>"
        f"<div style='font-size:18px;font-weight:700'>"
        f"{'🔥' if strong_count >= 5 else '⚠️' if len(jobs) < 5 else '🚀'} "
        f"{len(jobs)} вакансій для «{primary_role}»</div>"
        f"<div style='font-size:13px;opacity:.85;margin-top:3px'>"
        f"🟢 Сильних: {strong_count} &nbsp;·&nbsp; 🟡 Хороших: {medium_count} &nbsp;·&nbsp; 📍 {city}</div>"
        f"</div>"
        f"<div style='display:flex;gap:10px'>"
        f"<span style='background:#ffffff22;color:white;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600'>"
        f"Score топ: {jobs[0].get('final_score',0) if jobs else 0}</span>"
        f"</div></div>",
        unsafe_allow_html=True
    )

    # ============================================================
    # ПРОФІЛЬ БЛОК
    # ============================================================
    with st.expander("🧠 Профіль", expanded=True):
        profile_changed = False
        roles  = list(profile.get("roles",  []))
        skills = list(profile.get("skills", []))

        # Strength bar
        ss = min(100, len(roles)*20 + len(skills)*10 + (10 if profile.get("level") else 0))
        fc = '#22c55e' if ss>=70 else '#f59e0b' if ss>=40 else '#ef4444'
        lb = ("🟢 Сильний" if ss>=70 else "🟡 Середній" if ss>=40 else "🔴 Слабкий")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px'>"
            f"<span style='color:#e5e7eb;font-size:13px;font-weight:600'>{lb}</span>"
            f"<div style='flex:1;height:5px;border-radius:3px;background:#334155'>"
            f"<div style='width:{ss}%;height:100%;border-radius:3px;background:{fc};transition:width .3s'></div>"
            f"</div><span style='color:#64748b;font-size:12px'>{ss}%</span></div>",
            unsafe_allow_html=True
        )
        if ss < 40:
            st.markdown("<p style='color:#94a3b8;font-size:12px;margin:0 0 8px'>💡 Додай роль і хоча б 2 навички</p>",
                        unsafe_allow_html=True)
        elif ss < 70:
            need = max(0, 3-len(skills))
            if need:
                st.markdown(f"<p style='color:#94a3b8;font-size:12px;margin:0 0 8px'>💡 Додай ще {need} навичок</p>",
                            unsafe_allow_html=True)

        if not roles:
            st.markdown(
                "<div style='text-align:center;padding:8px 0 4px;"
                "color:#475569;font-size:12px'>Обери роль для початку</div>",
                unsafe_allow_html=True
            )
            _empty_list = ["Sales Manager", "Developer", "Marketing", "Cook", "Driver"]
            _ec = st.columns(len(_empty_list))
            for _ei, _er in enumerate(_empty_list):
                with _ec[_ei]:
                    if st.button(_er, key=f"empty_{_er}", use_container_width=True):
                        profile["roles"] = [_er]
                        st.session_state.profile = profile
                        st.session_state.pop("jobs_cache", None)
                        st.rerun()

        col1, col2, col3 = st.columns([2, 2, 1])

        # ─── ROLES ───
        with col1:
            st.markdown("<p class='sec-header'>Ролі</p>", unsafe_allow_html=True)
            if roles:
                for _i in range(0, len(roles), 4):
                    _row = roles[_i:_i+4]
                    _cols = st.columns(4)
                    for _j, _r in enumerate(_row):
                        with _cols[_j]:
                            if st.button(f"{_r}  ×", key=f"xr_{_r}"):
                                roles.remove(_r)
                                profile["roles"] = roles
                                st.session_state.profile = profile
                                st.session_state.pop("jobs_cache", None)
                                st.rerun()

            # Add via Enter
            def _on_role_add():
                _v = st.session_state.get("role_input", "").strip()
                if _v and _v not in roles:
                    roles.append(_v)
                    profile["roles"] = roles
                    st.session_state.profile = profile
                    st.session_state["role_input"] = ""
                    st.session_state["_role_added"] = _v
                    st.session_state.pop("jobs_cache", None)
            st.text_input("", key="role_input",
                          placeholder="+ роль  (Enter)",
                          label_visibility="collapsed",
                          on_change=_on_role_add)
            if st.session_state.pop("_role_added", None):
                st.success("Роль додано")

            # Compact suggestions
            sugg = []
            if roles:
                for _r in roles:
                    for _a in ROLE_CLUSTERS.get(_r.lower(), []):
                        _cap = _a.title()
                        if _cap not in roles and _cap not in sugg:
                            sugg.append(_cap)
                sugg = sugg[:3]
            else:
                sugg = ["Sales Manager", "Developer", "Cook"]
            if sugg:
                _sgcols = st.columns(len(sugg))
                for _si, _sg in enumerate(sugg):
                    with _sgcols[_si]:
                        if st.button(f"+ {_sg}", key=f"sug_{_sg}", help=f"+ {_sg}"):
                            if _sg not in roles:
                                roles.append(_sg)
                                profile["roles"] = roles
                                profile_changed = True

        # ─── SKILLS ───
        with col2:
            st.markdown("<p class='sec-header'>Навички</p>", unsafe_allow_html=True)
            if skills:
                for _i in range(0, len(skills), 4):
                    _row = skills[_i:_i+4]
                    _cols = st.columns(4)
                    for _j, _s in enumerate(_row):
                        with _cols[_j]:
                            if st.button(f"{_s}  ×", key=f"xs_{_s}"):
                                skills.remove(_s)
                                profile["skills"] = skills
                                st.session_state.profile = profile
                                st.session_state.pop("jobs_cache", None)
                                st.rerun()

            # Add via Enter
            def _on_skill_add():
                _v = st.session_state.get("skill_input", "").strip()
                if _v and _v not in skills:
                    skills.append(_v)
                    profile["skills"] = skills
                    st.session_state.profile = profile
                    st.session_state["skill_input"] = ""
                    st.session_state["last_added_skill"] = _v
                    st.session_state.pop("jobs_cache", None)
            st.text_input("", key="skill_input",
                          placeholder="+ додати навичку (Enter)",
                          label_visibility="collapsed",
                          on_change=_on_skill_add)
            st.caption("↵ Enter щоб додати")
            st.session_state.pop("last_added_skill", None)

        # ─── LEVEL ─── 3 chip-buttons in one row
        with col3:
            st.markdown("<p class='sec-header'>Рівень</p>", unsafe_allow_html=True)
            _cur_lvl = profile.get("level", "junior")
            if _cur_lvl not in ["junior", "middle", "senior"]:
                _cur_lvl = "junior"
            _lc = st.columns(3)
            for _i, _lvl in enumerate(["junior", "middle", "senior"]):
                _btype = "primary" if _lvl == _cur_lvl else "secondary"
                if _lc[_i].button(_lvl.capitalize(), key=f"lvl_{_lvl}",
                                  type=_btype, use_container_width=True):
                    if _lvl != _cur_lvl:
                        profile["level"] = _lvl
                        profile_changed = True

        if profile_changed:
            st.session_state.profile = profile
            st.session_state.pop("jobs_cache", None)
            st.rerun()

    # ============================================================
    # FILTERS — always visible
    # ============================================================
    st.markdown("<div class='s-card' style='margin-top:12px'>", unsafe_allow_html=True)
    st.markdown("<p class='sec-header'>Фільтри</p>", unsafe_allow_html=True)

    _salary_opts = ["Не важливо", "$1000+", "$2000+", "$3000+"]
    _remote_opts = ["Не важливо", "Remote", "Office", "Hybrid"]

    # Filters — init from prefs ONCE, never override after
    if "flt_salary" not in st.session_state:
        _v = prefs.get("salary", "Не важливо")
        st.session_state.flt_salary = _v if _v in _salary_opts else "Не важливо"
    if "flt_remote" not in st.session_state:
        _v = prefs.get("remote", "Не важливо")
        st.session_state.flt_remote = _v if _v in _remote_opts else "Не важливо"

    ff1, ff2 = st.columns(2)
    with ff1:
        new_sal = st.selectbox("💰 Зарплата", _salary_opts, key="flt_salary")
    with ff2:
        new_rem = st.selectbox("🏠 Формат", _remote_opts, key="flt_remote")

    # Only sync when widget value differs from stored pref
    if new_sal != prefs.get("salary") or new_rem != prefs.get("remote"):
        prefs["salary"] = new_sal
        prefs["remote"] = new_rem
        st.session_state.preferences = prefs
        st.session_state.pop("jobs_cache", None)
        st.rerun()

    # Fix 9: active pref chips
    pref_tags = []
    if prefs.get("salary","Не важливо") != "Не важливо": pref_tags.append(f"💰 {prefs['salary']}")
    if prefs.get("remote","Не важливо")  != "Не важливо": pref_tags.append(f"🏠 {prefs['remote']}")
    if prefs.get("english","Не важливо") != "Не важливо": pref_tags.append(f"🇬🇧 {prefs['english']}")
    if pref_tags:
        _ptags_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-top:10px'>"
        for _pt in pref_tags:
            _ptags_html += f"<span class='chip chip-pref-active'>{_pt}</span>"
        _ptags_html += "</div>"
        st.markdown(_ptags_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # СТАТИСТИКА
    # ============================================================
    st.markdown("<p class='sec-header'>Результати</p>", unsafe_allow_html=True)

    fpersrc = {}
    for j in jobs:
        src = j.get("source","Other")
        fpersrc[src] = fpersrc.get(src,0)+1

    if source_stats and isinstance(list(source_stats.values())[0], dict):
        active_src = [s for s in source_stats if source_stats[s]["found"] > 0]
        if active_src:
            cols = st.columns(len(active_src)+1)
            for i, src in enumerate(active_src):
                s = source_stats[src]
                s["final"] = fpersrc.get(src,0)
                cols[i].metric(src, s["found"], delta=f"✅{s['final']}")
                cols[i].caption(f"valid: {s['valid']} · final: {s['final']}")
            cols[-1].metric("✅ Відібрано", len(jobs))
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("🌐 Jooble",  source_stats.get("Jooble",0))
        c2.metric("💻 DOU",     source_stats.get("DOU",0))
        c3.metric("🔎 SerpAPI", source_stats.get("SerpAPI",0))
        c4.metric("✅ Відібрано", len(jobs))

    if filter_stats and isinstance(filter_stats, dict):
        bad = filter_stats.get("original",0) - filter_stats.get("clean",0)
        if bad > 0: st.warning(f"⚠️ Відфільтровано {bad} поганих лінків")
        st.caption(
            f"Фільтр: {filter_stats.get('original',0)} → "
            f"valid: {filter_stats.get('clean',0)} → "
            f"fresh: {filter_stats.get('fresh',0)} → "
            f"role: {filter_stats.get('role_match',0)} → "
            f"final: {filter_stats.get('quality',len(jobs))}"
        )

    if not jobs:
        st.warning("😕 Вакансій не знайдено. Спробуй змінити критерії.")
        if st.button("← Змінити критерії"):
            st.session_state.pop("jobs_cache",None)
            st.session_state.step = "input"
            st.rerun()
    elif len(jobs) < 5:
        st.warning("⚠️ Мало вакансій — показую що є")

    if jobs:
        strong = [j for j in jobs if j["final_score"] >= 70]
        medium = [j for j in jobs if 40 <= j["final_score"] < 70]

        # ---- TOP 3 ----
        st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
        st.markdown("<p class='sec-header'>ТОП вакансії</p>", unsafe_allow_html=True)
        top3   = jobs[:3]
        medals = ["🥇","🥈","🥉"]
        tcols  = st.columns(min(3, len(top3)))
        for i, col in enumerate(tcols):
            if i < len(top3):
                jb    = top3[i]
                sc    = jb["final_score"]
                bg    = "#14532d22" if sc>=70 else "#78350f22" if sc>=40 else "#1e293b"
                bord  = "#22c55e" if sc>=70 else "#f59e0b" if sc>=40 else "#334155"
                badge = "#22c55e" if sc>=70 else "#f59e0b" if sc>=40 else "#64748b"
                with col:
                    st.markdown(f"""
<div style="border:1px solid {bord};border-radius:12px;padding:16px;background:{bg}">
  <div style="font-size:20px;margin-bottom:6px">{medals[i]}</div>
  <div style="font-weight:700;font-size:14px;color:#e5e7eb;margin-bottom:4px">{jb['title'][:50]}</div>
  <div style="color:#94a3b8;font-size:12px">{jb.get('company','')[:30]} · {jb.get('source','')}</div>
  <div style="color:#64748b;font-size:11px;margin-top:2px">📍 {jb.get('location','')[:25]}</div>
  <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">
    <span style="background:{badge};color:white;padding:2px 10px;border-radius:20px;font-size:12px">Score: {sc}</span>
    <span style="background:#4f46e5;color:white;padding:2px 10px;border-radius:20px;font-size:12px">{jb.get('label','—')}</span>
  </div>
</div>""", unsafe_allow_html=True)
                    st.markdown(f"[👉 Відкрити]({jb['link']})")

        st.divider()
        if strong: st.success(f"🟢 Сильні (70%+): {len(strong)}")
        if medium: st.warning(f"🟡 Хороші (40–70%): {len(medium)}")

        # ---- ALL JOBS — card UI ----
        st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
        st.markdown(f"<p class='sec-header'>Всі вакансії ({len(jobs)})</p>", unsafe_allow_html=True)

        valid_jobs = [j for j in jobs if j.get("link") and j["link"].count("/") >= 3]
        if len(valid_jobs) >= 5: jobs = valid_jobs

        show_top = st.toggle("⭐ Тільки топ (70%+)", value=False)
        disp = [j for j in jobs if j["final_score"]>=70] if show_top else jobs

        bad_pats = ["search","jobs?","vacancies?","page=","query=","filter","resume","candidate","cv"]

        for i, job in enumerate(disp):
            sc       = job.get("final_score", 0)
            link     = job.get("link", "")
            bad_link = not link or any(p in link.lower() for p in bad_pats) or link.count("/")<3
            badge_bg = "#22c55e" if sc>=70 else "#f59e0b" if sc>=40 else "#64748b"
            card_brd = "#22c55e44" if sc>=70 else "#f59e0b44" if sc>=40 else "#334155"
            lbl      = job.get("label","—")

            reas, warns = explain_match(job, profile, city)
            act, act_col, top_sig = decision_hint(sc, reas, warns)
            reasons_html = "  ·  ".join(reas[:3]) if reas else ""

            # ── Card header (always visible) ──
            st.markdown(f"""
<div style="border:1px solid {card_brd};border-radius:12px;padding:12px 16px;
background:#1e293b;margin-bottom:6px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
    <div style="flex:1;min-width:0">
      <div style="font-weight:700;font-size:14px;color:#e5e7eb;margin-bottom:3px;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{job.get('title','Без назви')[:60]}</div>
      <div style="color:#94a3b8;font-size:12px;margin-bottom:4px">
        🏢 {job.get('company','-')[:35]}  ·  📍 {job.get('location','-')[:25]}  ·  🔎 {job.get('source','-')}</div>
      <div style="color:#64748b;font-size:11px">{reasons_html}</div>
    </div>
    <div style="flex-shrink:0;text-align:right">
      <span style="background:{badge_bg};color:white;padding:3px 10px;border-radius:20px;
            font-size:12px;font-weight:600;display:block;margin-bottom:4px">Score {sc}</span>
      <span style="background:#4f46e5;color:white;padding:2px 8px;border-radius:20px;
            font-size:11px;display:block">{lbl}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            # ── Inline description (no expander) ──
            if job.get("description"):
                _desc = job["description"][:220].strip()
                st.markdown(
                    f"<div style='color:#64748b;font-size:12px;margin:-4px 0 6px;line-height:1.5'>"
                    f"{_desc}…</div>",
                    unsafe_allow_html=True,
                )
            if warns and sc < 40:
                st.caption("⚠️ " + " | ".join(warns[:2]))

            # ── Card actions — one row ──
            _ca1, _ca2, _ca3, _ca4 = st.columns([3, 1, 1, 1])
            with _ca1:
                if link and not bad_link:
                    st.markdown(f"[👉 Відкрити вакансію]({link})")
                elif link:
                    st.markdown(f"[🔗 Спробувати]({link})")
            with _ca2:
                if st.button("✅ Apply", key=f"ap_{i}"):
                    if link not in st.session_state.applied:
                        st.session_state.applied.append(link)
                    st.success("Додано")
            with _ca3:
                if st.button("❌ Skip", key=f"sk_{i}"):
                    if link not in st.session_state.skipped:
                        st.session_state.skipped.append(link)
            with _ca4:
                if st.button("✉️ Відгук", key=f"cov_btn_{i}"):
                    st.session_state[f"cov_{i}_open"] = not st.session_state.get(f"cov_{i}_open", False)

            # ── Cover letter ──
            if st.session_state.get(f"cov_{i}_open"):
                cov_key = f"cov_{i}"
                if cov_key not in st.session_state:
                    st.session_state[cov_key] = ""
                cstyle = st.radio("Стиль:", ["short","medium","strong"], horizontal=True,
                                  key=f"sty_{i}",
                                  format_func=lambda x: {"short":"⚡ Короткий","medium":"📝 Середній","strong":"🔥 Сильний"}[x])
                if st.button("Згенерувати", key=f"cov_gen_{i}"):
                    st.session_state[cov_key] = generate_cover(job, profile, cstyle)
                if st.session_state.get(cov_key):
                    st.text_area("Відгук:", st.session_state[cov_key], height=180, key=f"cov_txt_{i}")

            if i < len(disp)-1:
                st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

        st.divider()
        with st.expander("❌ Чому деякі не в ТОП"):
            for lj in sorted(jobs, key=lambda x: x.get("final_score",0))[:5]:
                lt = (lj.get("title","") + lj.get("description","")).lower()
                if not has_role_match(lj, profile): rsn = "❌ Інша роль"
                elif not any(s.lower() in lt for s in profile.get("skills",[])): rsn = "⚠️ Мало навичок"
                else: rsn = "📉 Слабкий матч"
                st.caption(f"{lj.get('title','-')} → {rsn} ({lj.get('final_score',0)})")

        st.divider()

# ============================================================
# FOOTER
# ============================================================
fc1, fc2 = st.columns([1, 4])
with fc1:
    if st.button("🔄 Новий пошук", use_container_width=True):
        st.session_state.clear()
        st.rerun()
with fc2:
    if st.button("🤖 AI аналіз", use_container_width=True):
        result = ask_ai("Скажи коротко що таке ефективний sales pipeline")
        st.write(result)