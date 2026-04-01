import requests
import streamlit as st


def ask_ai(prompt, system="Ти AI асистент для пошуку роботи. Відповідай українською, коротко і чітко."):
    """
    Стабільний AI агент через Anthropic API.
    Працює на claude-haiku-4-5 — швидкий і дешевий.
    """
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return "❌ ANTHROPIC_API_KEY не знайдено в Secrets"

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    except Exception as e:
        return f"❌ Помилка AI: {str(e)[:100]}"


def analyze_job_ai(job, profile):
    """Аналізує вакансію через AI — чому підходить чи ні"""
    prompt = f"""Вакансія: {job.get('title')} в {job.get('company')}
Опис: {job.get('description', '')[:300]}

Кандидат: ролі={profile.get('roles')}, навички={profile.get('skills')}, рівень={profile.get('level')}

Дай 2-3 речення: чому ця вакансія підходить або ні для цього кандидата."""

    return ask_ai(prompt)


def generate_cover_ai(job, profile, style="medium"):
    """Генерує cover letter через AI"""
    styles = {
        "short":  "Дуже короткий cover letter — 3-4 речення",
        "medium": "Стандартний cover letter — 2-3 абзаци",
        "strong": "Сильний продаючий cover letter — 3-4 абзаци з конкретикою",
    }

    prompt = f"""Напиши {styles.get(style, styles['medium'])} для:
Вакансія: {job.get('title')} в {job.get('company')}
Кандидат: {profile.get('experience_years')} років досвіду, ролі: {profile.get('roles')}, навички: {profile.get('skills')}
Мова: українська"""

    return ask_ai(prompt, system="Ти пишеш cover letter для пошуку роботи. Будь конкретним і переконливим.")