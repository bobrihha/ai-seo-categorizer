import pandas as pd
from openai import OpenAI
import json
import time
import os
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
API_KEY = "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"  # <--- ВСТАВЬ КЛЮЧ
INPUT_CSV = 'blog-export-2025-november-26-0246.csv'
CATEGORIES_FILE = 'крайняя иерархия рубрики спорт.txt' # Файл клиента
OUTPUT_FILE = 'TAGS_RESULT.csv'
SAVE_EVERY = 50

client = OpenAI(api_key=API_KEY)

def load_categories(filepath):
    """Читает файл клиента и делает плоский список категорий"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        # Просто отдадим этот текст ИИ как справочник
        return text
    except Exception as e:
        print(f"Ошибка чтения списка рубрик: {e}")
        return ""

# Загружаем рубрики в память
CATEGORIES_LIST = load_categories(CATEGORIES_FILE)

def clean_html(html_text):
    if not isinstance(html_text, str): return ""
    soup = BeautifulSoup(html_text, "html.parser")
    for script in soup(["script", "style"]): script.extract()
    text = soup.get_text(separator=' ')
    return " ".join(text.split())[:3000]

def analyze_tags(title, content_text):
    # ПРОМПТ ДЛЯ ТЭГГИНГА
    prompt = f"""
    Ты контент-менеджер.
    СТАТЬЯ: {title}
    Текст: {content_text}
    
    ВОТ СПИСОК ДОПУСТИМЫХ РУБРИК (ИЕРАРХИЯ):
    {CATEGORIES_LIST}
    
    ЗАДАЧА:
    1. Проанализируй статью.
    2. Выбери из списка от 1 до 3 самых подходящих КОНЕЧНЫХ рубрик (самый нижний уровень вложенности).
    3. Не придумывай свои! Бери только из списка.
    
    Пример: Если статья про "Жим лежа", выбери "Пауэрлифтинг" и "Грудные мышцы" (если они есть в списке).
    
    Также сделай H1, SEO Title, Description.
    
    Ответ JSON:
    {{
        "selected_categories": ["Рубрика 1", "Рубрика 2"],
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
    print("--- ЗАПУСК ТЭГГИНГА ПО СПИСКУ КЛИЕНТА ---")
    
    if not CATEGORIES_LIST:
        print("СТОП! Не удалось прочитать файл с рубриками.")
        return

    try:
        df_source = pd.read_csv(INPUT_CSV)
        print(f"Статей в базе: {len(df_source)}")
    except:
        print("Нет CSV файла!")
        return

    # Логика продолжения работы (если упадет)
    results = []
    start_index = 0
    if os.path.exists(OUTPUT_FILE):
        try:
            df_exist = pd.read_csv(OUTPUT_FILE)
            results = df_exist.to_dict('records')
            start_index = len(results)
            print(f"Продолжаем с {start_index}-й статьи...")
        except: pass

    df_process = df_source.iloc[start_index:].copy()

    for i, (index, row) in enumerate(df_process.iterrows()):
        real_cnt = start_index + i + 1
        
        if real_cnt % 10 == 0: print(f"Обработано {real_cnt}...")
            
        ai_res = analyze_tags(row['Title'], clean_html(row['Content']))
        
        if ai_res:
            # Превращаем список категорий в строку через запятую
            cats = ai_res.get('selected_categories', [])
            if isinstance(cats, list):
                cats_str = ", ".join(cats)
            else:
                cats_str = str(cats)

            results.append({
                'post_id': row['ID'],
                'url': row['Permalink'],
                'found_categories': cats_str, # <--- ТУТ БУДУТ ТЕГИ
                'new_h1': ai_res.get('new_h1'),
                'seo_title': ai_res.get('seo_title'),
                'seo_description': ai_res.get('seo_description')
            })

        # Сохранение каждые 50 шт
        if real_cnt % SAVE_EVERY == 0 or real_cnt == len(df_source):
            pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            print(f"   [Сохранено {real_cnt}]")

    print("ГОТОВО!")

if __name__ == "__main__":
    main()
