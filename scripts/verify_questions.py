#!/usr/bin/env python3
"""
Валидация вопросов - проверка сложности и качества неправильных ответов.
"""

import sqlite3
import json

def verify_questions(database_path: str = "quiz_bot.db"):
    """Проверка вопросов."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    issues = []
    
    print("=" * 60)
    print("ПРОВЕРКА БАЗЫ ВОПРОСОВ")
    print("=" * 60)
    
    # 1. Проверка сложности
    print("\n1. Распределение по сложности:")
    cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty")
    diff_stats = dict(cursor.fetchall())
    
    for diff, count in [('EASY', 0), ('MEDIUM', 0), ('HARD', 0)]:
        actual = diff_stats.get(diff, 0)
        status = "OK" if actual > 100 else "ERROR"
        print(f"   {status} {diff}: {actual}")
        
        if actual < 100:
            issues.append(f"Мало вопросов для {diff}: {actual}")
    
    # 2. Проверка неправильных ответов
    print("\n2. Проверка неправильных ответов:")
    
    # Считаем плохие ответы
    cursor.execute("""
        SELECT COUNT(*) FROM questions 
        WHERE wrong_answers LIKE '%Вариант%'
           OR wrong_answers LIKE '%Альтернатива%'
           OR wrong_answers LIKE '%Другой вариант%'
           OR wrong_answers LIKE '%Неверный%'
    """)
    bad_count = cursor.fetchone()[0]
    
    print(f"   Вопросов с заглушками: {bad_count}")
    
    if bad_count > 100:
        issues.append(f"Много вопросов с заглушками: {bad_count}")
    
    # 3. Примеры вопросов
    print("\n3. Примеры вопросов:")
    cursor.execute("""
        SELECT text, correct_answer, wrong_answers, difficulty, category
        FROM questions
        LIMIT 3
    """)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        text, correct, wrong_json, diff, cat = row
        try:
            wrong = json.loads(wrong_json) if wrong_json else []
        except:
            wrong = [wrong_json]
        
        print(f"\n   Вопрос {i} ({diff}, {cat}):")
        print(f"   Q: {text[:60]}...")
        print(f"   A: {correct}")
        print(f"   W: {wrong}")
    
    # Итог
    print("\n" + "=" * 60)
    if issues:
        print("ERROR Найдены проблемы:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nРекомендации:")
        print("   python scripts/fix_hard_difficulty.py")
        print("   python scripts/improve_wrong_answers.py")
    else:
        print("OK Все проверки пройдены!")
    print("=" * 60)
    
    conn.close()
    return len(issues) == 0

if __name__ == "__main__":
    verify_questions()
