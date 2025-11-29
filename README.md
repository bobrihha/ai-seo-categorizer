Инструкция по запуску demo_bot.py

1) Положи `blog-export-2025-november-26-0246.csv` в ту же папку, где `demo_bot.py`.

2) Установи зависимости (рекомендуется виртуальное окружение):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3) Настрой API ключ OpenAI:
- Создай файл `.env` в корне проекта (можно скопировать из `.env.example`):
  ```bash
  cp .env.example .env
  ```
- Открой `.env` и вставь свой ключ:
  ```
  OPENAI_API_KEY=sk-ваш_ключ
  ```

4) Запусти скрипт:

```bash
python3 demo_bot.py
```

После успешного выполнения появится файл `demo_result.csv` с результатами. Если возникли ошибки, проверь правильность названий колонок в CSV (ожидаются `Title`, `Content`, `Permalink`, `ID`).
