"""
Валидация качества сгенерированных неправильных ответов.
"""
import sqlite3
import json
from typing import List, Tuple


def validate_distractors(database_path: str = "quiz_bot.db", sample_size: int = 100):
    """Проверка случайной выборки вопросов."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Случайная выборка
    cursor.execute("""
        SELECT id, text, correct_answer, wrong_answers, category
        FROM questions
        WHERE wrong_answers NOT LIKE '%Вариант%'
        AND wrong_answers NOT LIKE '%вариант%'
        ORDER BY RANDOM()
        LIMIT ?
    """, (sample_size,))
    
    questions = cursor.fetchall()
    conn.close()
    
    print(f"Валидация {len(questions)} вопросов\n")
    
    issues = []
    for q_id, text, correct, wrong_json, category in questions:
        try:
            wrong = json.loads(wrong_json)
        except json.JSONDecodeError:
            issues.append((q_id, "Невалидный JSON в wrong_answers"))
            continue
        
        # Проверка 1: Количество вариантов
        if len(wrong) != 3:
            issues.append((q_id, f"Не 3 варианта: {len(wrong)}"))
        
        # Проверка 2: Правильный ответ не в wrong_answers
        if correct.lower() in [w.lower() for w in wrong]:
            issues.append((q_id, "Правильный ответ в wrong_answers"))
        
        # Проверка 3: Тип совпадает (эвристика)
        if correct.isdigit() and not all(w.isdigit() for w in wrong):
            issues.append((q_id, "Тип не совпадает (год vs текст)"))
        
        # Проверка 4: Длина вариантов
        for i, w in enumerate(wrong):
            if len(w) > 64:
                issues.append((q_id, f"Вариант {i+1} слишком длинный: {len(w)} символов"))
    
    # Отчёт
    print("=" * 60)
    print("ОТЧЁТ ВАЛИДАЦИИ")
    print("=" * 60)
    print(f"Проверено: {len(questions)} вопросов")
    print(f"Проблем: {len(issues)}")
    
    if issues:
        print("\nПроблемные вопросы:")
        for q_id, issue in issues[:10]:  # Показать первые 10
            print(f"  - Вопрос {q_id}: {issue}")
        
        if len(issues) > 10:
            print(f"  ... и ещё {len(issues) - 10} проблем")
    else:
        print("\nВсе вопросы прошли валидацию!")
    
    print("=" * 60)
    
    return len(issues) == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=100, help='Размер выборки')
    parser.add_argument('--db', default='quiz_bot.db', help='Путь к БД')
    args = parser.parse_args()
    
    is_valid = validate_distractors(args.db, args.sample)
    exit(0 if is_valid else 1)
