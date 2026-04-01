from dou import search_dou
from djinni import search_djinni
from filter import is_relevant_job
from ai_score import calculate_score, should_apply, explain_score

def main():
    dou_jobs = search_dou()
    djinni_jobs = search_djinni()

    print(f"DOU jobs: {len(dou_jobs)}")
    print(f"Djinni jobs: {len(djinni_jobs)}")

    jobs = dou_jobs + djinni_jobs

    # 🔥 ФІЛЬТР
    jobs = [j for j in jobs if is_relevant_job(j)]

    # 🔥 СОРТУВАННЯ
    jobs = sorted(jobs, key=calculate_score, reverse=True)

    print("\n🔥 ТОП ВАКАНСІЇ + AI ОЦІНКА:\n")

    for j in jobs[:10]:
        decision = should_apply(j)
        reason = explain_score(j)

        print(f"[{j.source}] {j.title}")
        print(f"🏢 {j.company} | {j.city}")
        print(f"📊 {decision}")
        print(f"🧠 Причина: {reason}")
        print(j.url)
        print("-" * 60)

if __name__ == "__main__":
    main()