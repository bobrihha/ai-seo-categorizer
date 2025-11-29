import pandas as pd
from openai import OpenAI
import json
import time
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

# --- НАСТРОЙКИ ---
API_KEY = os.environ.get("OPENAI_API_KEY")
INPUT_FILE = 'blog-export-2025-november-26-0246.csv'
OUTPUT_FILE = 'FINAL_SUBMISSION.csv' # Назовем файл так, чтобы не путать

client = OpenAI(api_key=API_KEY)

def clean_html(html_text):
    if not isinstance(html_text, str): return ""
    soup = BeautifulSoup(html_text, "html.parser")
    for script in soup(["script", "style"]): script.extract()
    text = soup.get_text(separator=' ')
    return " ".join(text.split())[:3500]

def analyze_deeply(title, content_text):
    # ПРОМПТ С ИСПРАВЛЕННОЙ ЛОГИКОЙ (ПОДТЯГИВАНИЯ = СПОРТ)
    prompt = f"""
    Ты архитектор спортивной энциклопедии. Роль: Строгий редактор.
    
    СТАТЬЯ:
    Заголовок: {title}
    Текст: {content_text}
    
    ЗАДАЧА:
    Построй иерархию из 3-х уровней.
    
    !!! КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО !!!
    Если статья описывает КОНКРЕТНОЕ УПРАЖНЕНИЕ (подтягивания, жим, присед, бег) или ПРОГРАММУ ТРЕНИРОВОК — это ВСЕГДА "Level 1 = Виды спорта" -> "Level 2 = Силовые виды" (или Фитнес).
    НЕ СТАВЬ упражнения в "Медицину" или "Науку"!
    
    ПРАВИЛА ДЛЯ LEVEL 3 (Тег):
    1. Именительный падеж, Единственное число.
    2. Стандартный термин (например: "Подтягивание", а не "Как подтянуться").
    
    СТРУКТУРА:
    1. LEVEL 1 (Корневой). Строго один из:
       [Виды спорта, История и наука, Соревнования, Персоны в спорте, Организации].
       
    2. LEVEL 2 (Направление).
       - Если Lvl1="Виды спорта" -> Силовые виды, Единоборства, Легкая атлетика, Фитнес.
       - Если Lvl1="История и наука" -> Спортивное питание, Фармакология, Спортивная медицина (только болезни/травмы!), Физиология.
    
    3. LEVEL 3 (Тег). Конкретный предмет статьи.
    
    Ответ верни строго в JSON:
    {{
        "lvl1": "...",
        "lvl2": "...",
        "lvl3": "...",
        "new_h1": "...",
        "seo_title": "...",
        "seo_description": "..."
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, 
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return None

def main():
    print("--- ЗАПУСК ФИНАЛЬНОЙ ОБРАБОТКИ (ВСЕ СТАТЬИ) ---")
    
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Файл найден. Всего статей: {len(df)}")
    except FileNotFoundError:
        print("ОШИБКА: Файл с данными не найден!")
        return

    # МЫ БОЛЬШЕ НЕ ИСПОЛЬЗУЕМ df_test. МЫ БЕРЕМ ВСЁ.
    df_process = df.copy() 
    
    results = []
    start_time = time.time()

    for index, row in df_process.iterrows():
        # Выводим прогресс каждые 10 статей
        if index % 10 == 0: 
            print(f"Обработано {index}/{len(df_process)}...")
            
        ai_res = analyze_deeply(row['Title'], clean_html(row['Content']))
        
        if ai_res:
            results.append({
                'post_id': row['ID'],
                'url': row['Permalink'],
                'category_lvl1': ai_res.get('lvl1'),
                'category_lvl2': ai_res.get('lvl2'),
                'category_lvl3': ai_res.get('lvl3'),
                'new_h1': ai_res.get('new_h1'),
                'seo_title': ai_res.get('seo_title'),
                'seo_description': ai_res.get('seo_description')
            })

    # Сохраняем
    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"\nГОТОВО! Заняло времени: {round((time.time() - start_time)/60, 1)} мин.")
    print(f"Итоговый файл: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
