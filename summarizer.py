import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Завантажуємо змінні оточення (включаючи GEMINI_API_KEY)
load_dotenv()

SYSTEM_PROMPT = """Ти — досвідчений Technical Project Manager та асистент. 
Нижче наведено автоматичний транскрипт робочого дзвінка. 
Твоє завдання — перетворити цей текст на структурований інженерний конспект у форматі Markdown.

Створи нотатку за такою структурою:
# 📅 Мітинг від [Сьогоднішня дата]
## 📝 Коротке Самері
[Один-два абзаци: про що взагалі була розмова, яка головна мета дзвінка].
## 🎯 Головні Рішення (Key Decisions)
* [Тільки прийняті рішення або затверджені архітектурні зміни].
## 🛠 Action Items (Задачі)
* [ ] **Хто** - **Що має зробити** (якщо невідомо хто, просто напиши задачу).
## 🗣 Ключові Тези та Контекст
* [Стислий переказ важливих обговорень, ідей, згаданих багів, технологій чи проблем].

Правила:
- Ігноруй Small talk (розмови про погоду, привітання, жарти).
- Виправляй очевидні технічні терміни, якщо нейромережа почула їх неправильно.
- Пиши чітко, професійно та лаконічно.
- Виведи ТІЛЬКИ готовий Markdown-код, без вступних слів."""

def summarize_text(transcript_path="raw_transcript.txt"):
    """
    Відправляє текст транскрипту до Gemini для створення самері.
    """
    if not os.path.exists(transcript_path):
        print(f"Файл {transcript_path} не знайдено.")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "твій_ключ_тут":
        print("Помилка: GEMINI_API_KEY не знайдено. Будь ласка, створіть файл .env з вашим ключем.")
        return None

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    if not transcript_text.strip():
        print("Транскрипт порожній.")
        return None

    print("Відправлення тексту до Gemini для осмислення...")
    
    try:
        # Ініціалізація клієнта
        client = genai.Client()

        # Виклик моделі (наприклад, gemini-2.5-flash)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=transcript_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )

        summary = response.text
        summary_path = "summary.md"
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        print(f"Конспект успішно згенеровано та збережено у {summary_path}")
        return summary_path
        
    except Exception as e:
        print(f"Помилка при зверненні до Gemini: {e}")
        return None

if __name__ == "__main__":
    summarize_text()
