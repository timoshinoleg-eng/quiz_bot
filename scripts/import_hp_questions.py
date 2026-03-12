"""Импорт вопросов по Гарри Поттеру из JSON файла (синхронная версия)."""
import json
import sqlite3
import os
from pathlib import Path

def import_questions():
    """Импортировать вопросы из hp_book1_questions.json."""
    json_path = Path(__file__).parent.parent / "hp_book1_questions.json"
    db_path = os.getenv('DATABASE_PATH', 'quiz_bot.db')
    
    # Убираем префикс async если есть
    if db_path.startswith('sqlite+aiosqlite:'):
        db_path = db_path.replace('sqlite+aiosqlite:', 'sqlite:')
    if db_path.startswith('sqlite:'):
        db_path = db_path[7:]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total = 0
    
    for difficulty, questions in data.items():
        for q in questions:
            cursor.execute("""
                INSERT INTO questions 
                (text, correct_answer, wrong_answers, explanation, 
                 difficulty, category, source, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                q["text"],
                q["correct_answer"],
                json.dumps(q["wrong_answers"], ensure_ascii=False),
                q.get("explanation", ""),
                difficulty,
                "entertainment",
                "harry_potter_book_1",
                1
            ))
            total += 1
    
    conn.commit()
    
    # Вывод статистики
    for d in ["easy", "medium", "hard"]:
        cursor.execute("SELECT COUNT(*) FROM questions WHERE difficulty = ?", (d,))
        count = cursor.fetchone()[0]
        print(f"  {d}: {count} вопросов")
    
    conn.close()
    
    print(f"✅ Импортировано {total} вопросов")

if __name__ == "__main__":
    import_questions()
