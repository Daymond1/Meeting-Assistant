import os
import shutil
import datetime
import subprocess

def export_to_obsidian(summary_path="summary.md", vault_path=None):
    """
    Додає метадані до згенерованого конспекту та копіює його у сховище Obsidian.
    """
    if not os.path.exists(summary_path):
        print(f"Файл {summary_path} не знайдено.")
        return None

    # Якщо шлях не вказано, використовуємо локальну папку
    if not vault_path:
        vault_path = os.path.join(os.getcwd(), "02_Meetings")
        
    os.makedirs(vault_path, exist_ok=True)

    # Генеруємо назву файлу
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    file_name = f"{date_str}_Sync.md"
    destination_path = os.path.join(vault_path, file_name)

    # Зчитуємо текст
    with open(summary_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Замінюємо плейсхолдер дати, якщо він є
    content = content.replace("[Сьогоднішня дата]", f"{date_str} {time_str}")

    # Створюємо фронтметтер (метадані для Obsidian)
    frontmatter = f"""---
aliases: []
tags:
  - meeting
  - sync
date: {date_str}
time: {time_str}
---

"""

    final_content = frontmatter + content

    # Зберігаємо у Vault
    with open(destination_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print(f"Файл успішно експортовано до: {destination_path}")

    # Запускаємо git push (якщо це git-репозиторій)
    # Оскільки поки що ми тестуємо локально, ми огорнемо це у try/except
    try:
        # Перевіряємо, чи це git репозиторій
        is_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=vault_path, capture_output=True, text=True).returncode == 0
        
        if is_git:
            print("Синхронізація з віддаленим репозиторієм (git push)...")
            subprocess.run(["git", "add", "."], cwd=vault_path, check=True)
            subprocess.run(["git", "commit", "-m", f"Add meeting notes {date_str}"], cwd=vault_path, check=True)
            subprocess.run(["git", "push"], cwd=vault_path, check=True)
            print("Успішно завантажено в git!")
        else:
            print("Цільова папка не є git-репозиторієм, синхронізацію пропущено.")
    except subprocess.CalledProcessError as e:
        print(f"Помилка при виконанні git команд: {e}")
    except Exception as e:
        print(f"Непередбачена помилка під час синхронізації: {e}")

    return destination_path

if __name__ == "__main__":
    export_to_obsidian()
