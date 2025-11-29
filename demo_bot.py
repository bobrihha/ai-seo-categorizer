import os
import pandas as pd
from openai import OpenAI
import json
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
load_dotenv()
# Вставьте API Key прямо в переменную ниже или установите переменную окружения OPENAI_API_KEY
API_KEY = os.environ.get('OPENAI_API_KEY')
INPUT_FILE = 'blog-export-2025-november-26-0246.csv'
OUTPUT_FILE = 'demo_result.csv'
DEMO_LIMIT = 20  # Сколько статей обработать для теста

if not API_KEY:
    print("Пожалуйста, задайте OPENAI_API_KEY в файле .env или в окружении.")
    print("Пример (zsh): export OPENAI_API_KEY=sk-xxx")
    raise SystemExit(1)

client = OpenAI(api_key=API_KEY)
known_categories = [] # Память для рубрик


def clean_html(html_text):
    """Очищает HTML теги, оставляя только текст для экономии токенов"""
    if not isinstance(html_text, str):
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    # Удаляем скрипты и стили
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ')
    # Убираем лишние пробелы
    return " ".join(text.split())[:3500] # Берем первые 3500 символов


def analyze_with_ai(title, content_text, url):
    global known_categories
    
    prompt = f"""
    Ты SEO-архитектор сайта SportGuardian.
    
    СТАТЬЯ:
    Заголовок: {title}
    URL: {url}
    Текст: {content_text}
    
    УЖЕ СОЗДАННЫЕ РУБРИКИ:
    {", ".join(known_categories)}
    
    ЗАДАЧА:
    1. Назначь Рубрику (Lvl1) и Подрубрику (Lvl2).
       ВАЖНО: Сначала проверь, подходит ли статья в список "УЖЕ СОЗДАННЫЕ РУБРИКИ".
       Создавай новую ТОЛЬКО если статья совсем не подходит по смыслу.
       Избегай дублей (не делай "Питание" и "Еда", используй что-то одно).
    2. Проверь H1 (Заголовок). Если он скучный/короткий — предложи новый (new_h1). Иначе напиши "оставить текущий".
    3. Напиши SEO Title (до 60 зн) и Description (до 160 зн).
    
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
        # response.choices[0].message.content expected to be a JSON string
        data = json.loads(response.choices[0].message.content)
        
        # Запоминаем новую рубрику
        cat = data.get('category_lvl1')
        if cat and cat not in known_categories:
            known_categories.append(cat)
            
        return data
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return None


def main():
    print("--- ЗАПУСК ДЕМО ---")
    
    # 1. Читаем CSV
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Файл загружен. Всего строк: {len(df)}")
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        return

    # Берем первые N статей для демо
    df_demo = df.head(DEMO_LIMIT).copy()
    results = []

    print(f"Обрабатываем первые {DEMO_LIMIT} статей...")

    for index, row in df_demo.iterrows():
        title = row.get('Title') or row.get('title') or ''
        raw_content = row.get('Content') or row.get('content') or ''
        url = row.get('Permalink') or row.get('permalink') or ''
        post_id = row.get('ID') or row.get('id') or ''
        
        print(f"[{index+1}/{DEMO_LIMIT}] {title}")
        
        # Чистим текст перед отправкой
        clean_text = clean_html(raw_content)
        
        # Спрашиваем ИИ
        ai_res = analyze_with_ai(title, clean_text, url)
        
        if ai_res:
            results.append({
                'ID': post_id,
                'Original_Title': title,
                'URL': url,
                'Category_Lvl1': ai_res.get('category_lvl1'),
                'Category_Lvl2': ai_res.get('category_lvl2'),
                'New_H1': ai_res.get('new_h1'),
                'SEO_Title': ai_res.get('seo_title'),
                'SEO_Desc': ai_res.get('seo_description')
            })
            print(f"   -> Рубрика: {ai_res.get('category_lvl1')} | H1: {ai_res.get('new_h1')}")
        else:
            print("   -> AI вернул ошибку или пустой ответ; запись пропущена.")
        
        # Пауза не обязательна, но полезна для стабильности
        time.sleep(0.5)

    # Сохраняем результат
    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\nГОТОВО! Результат в файле: {OUTPUT_FILE}")
    print("Список созданных рубрик:", known_categories)


if __name__ == "__main__":
    main()
