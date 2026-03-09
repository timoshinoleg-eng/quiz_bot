# scripts/fix_wrong_answers.py
"""
Быстрое исправление неправильных ответов без LLM.
Использует эвристики для генерации вариантов.
"""

import sqlite3
import json
import random

def generate_plausible_wrong_answers(correct_answer, question):
    """Генерация правдоподобных неправильных ответов."""
    
    wrong = []
    
    # Стратегия 1: Если ответ содержит числа
    import re
    numbers = re.findall(r'\d+', correct_answer)
    if numbers:
        for num in numbers[:2]:
            wrong.append(correct_answer.replace(num, str(int(num) + 1)))
            wrong.append(correct_answer.replace(num, str(int(num) - 1)))
    
    # Стратегия 2: Если ответ содержит имена/названия
    if len(correct_answer.split()) > 1:
        words = correct_answer.split()
        if len(words) >= 2:
            wrong.append(f"{words[0]} (неверно)")
            wrong.append(f"Не {words[-1]}")
    
    # Стратегия 3: Общие заглушки на основе категории
    generic_wrong = [
        "Неверный вариант",
        "Другой ответ",
        "Не этот вариант",
        "Попробуй ещё",
        "Это неправильно"
    ]
    
    while len(wrong) < 3:
        wrong.append(random.choice(generic_wrong))
    
    # Обрезаем до 64 символов
    return [w[:64] for w in wrong[:3]]

def fix_database(database_path="quiz_bot.db"):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Находим вопросы с заглушками
    cursor.execute("""
        SELECT id, text, correct_answer, wrong_answers 
        FROM questions
        WHERE wrong_answers LIKE '%Вариант%'
        LIMIT 500
    """)
    
    questions = cursor.fetchall()
    print(f"📊 Найдено {len(questions)} вопросов с заглушками")
    
    updated = 0
    for q_id, text, correct, current in questions:
        wrong = generate_plausible_wrong_answers(correct, text)
        
        cursor.execute(
            "UPDATE questions SET wrong_answers = ? WHERE id = ?",
            (json.dumps(wrong), q_id)
        )
        updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Исправлено {updated} вопросов")

if __name__ == "__main__":
    fix_database()