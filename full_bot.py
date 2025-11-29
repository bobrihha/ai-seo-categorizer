import pandas as pd
from openai import OpenAI
import json
import time
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
API_KEY = "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"  # <--- ВСТАВЬ СЮДА СВОЙ КЛЮЧ
INPUT_FILE = 'blog-export-2025-november-26-0246.csv'  # Проверь имя файла!
OUTPUT_FILE = 'final_result.csv'

# Вшитая карта сайта от клиента
TAXONOMY_MAP = """
- Виды спорта
  - Летние виды спорта (Легкоатлетика, Плавание, Футбол, Теннис...)
  - Зимние виды спорта (Хоккей, Биатлон, Лыжи...)
  - Командные виды спорта (Волейбол, Регби...)
  - Боевые единоборства (Бокс, ММА, Самбо...)
  - Силовые виды спорта (Тяжёлая атлетика, Пауэрлифтинг, Культуризм, Армрестлинг)
  - Экстремальные виды спорта (Сноуборд, Паркур...)
  - Киберспорт
- Соревнования
  - Олимпийские игры
  - Чемпионаты мира
  - Национальные первенства (НХЛ, НБА...)
- Персоны в спорте
  - Спортсмены
  - Тренеры
- История и наука
  - Спортивная медицина (Травмы, Восстановление)
  - Спортивная наука (Биомеханика, Психология)
  - Методика тренировок (Периодизация, Планирование, Подготовка)
  - Питание спортсменов (включая Диеты и Спорпит)
  - Антидопинг
- Организации и структуры
  - Международные (МОК, ФИФА)
  - Спортивные учреждения
- Тематические теги
  - Рекорды
  - Экипировка и Инвентарь
  - Спортивные скандалы
"""

client = OpenAI(api_key=API_KEY)


def clean_html(html_text):
    """Очищает HTML для экономии токенов"""
    if not isinstance(html_text, str):
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ')
    return " ".join(text.split())[:3000]


def analyze_with_ai(title, content_text, url):
    prompt = f"""
    Ты контент-менеджер спортивной энциклопедии.
    
    СТАТЬЯ:
    Заголовок: {title}
    Текст: {content_text}
    
    КАРТА РУБРИК (Strict Taxonomy):
    {TAXONOMY_MAP}
    
    ЗАДАЧА:
    1. Распредели статью СТРОГО по этой карте.
    2. Category_Lvl1: Выбери одну из ГЛАВНЫХ категорий (Виды спорта, История и наука, Соревнования...).
    3. Category_Lvl2: Выбери самую ПОДХОДЯЩУЮ подкатегорию из глубины списка.
       - Пример: Если статья про "Жим лежа", то Lvl1="Виды спорта", Lvl2="Пауэрлифтинг" (или "Силовые виды спорта").
       - Пример: Если статья про "Диету", то Lvl1="История и наука", Lvl2="Питание спортсменов".
       - НЕ выдумывай свои названия. Бери из списка.
    
    4. Если статья про "Казино" или мусор — пометь как "Удалить".
    5. Сделай новый H1, SEO Title и Description.
    
    Ответ верни строго в JSON:
    {{
        "category_lvl1": "...",
        "category_lvl2": "...",
        "new_h1": "...",
        "seo_title": "...",
        "seo_description": "..."
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return None


def main():
    print("--- ЗАПУСК ПОЛНОЙ ОБРАБОТКИ ---")

    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Найдено статей: {len(df)}")
    except FileNotFoundError:
        print("ОШИБКА: Файл не найден. Проверь имя файла в скрипте!")
        return

    # Если хочешь обработать ВСЕ, убери .head()
    # Для теста можешь оставить .head(50)
    df_process = df.copy()

    results = []

    start_time = time.time()

    for index, row in df_process.iterrows():
        # Прогресс бар
        if index % 10 == 0:
            print(f"Обработано {index}/{len(df_process)}...")

        ai_res = analyze_with_ai(row['Title'], clean_html(row['Content']), row['Permalink'])

        if ai_res:
            results.append({
                'post_id': row['ID'],
                'url': row['Permalink'],
                'category_lvl1': ai_res.get('category_lvl1'),
                'category_lvl2': ai_res.get('category_lvl2'),
                'new_h1': ai_res.get('new_h1'),
                'seo_title': ai_res.get('seo_title'),
                'seo_description': ai_res.get('seo_description')
            })

        # Маленькая защита от перегрузки (можно убрать, если платный аккаунт)
        time.sleep(0.2)

    # Сохраняем с правильной кодировкой
    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    print(f"\nГОТОВО! Заняло времени: {round((time.time() - start_time)/60, 1)} мин.")
    print(f"Результат в файле: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
