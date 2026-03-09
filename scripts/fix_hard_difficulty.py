#!/usr/bin/env python3
"""
Исправление отсутствия вопросов для HARD сложности.
Принудительно распределяет 30% вопросов в HARD, 50% в MEDIUM, 20% в EASY.
"""

import sqlite3

def fix_hard_difficulty(database_path: str = "quiz_bot.db"):
    """Распределение сложности по процентам (не по ключевым словам)."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Получить все ID вопросов
    cursor.execute("SELECT id FROM questions ORDER BY id")
    all_ids = [row[0] for row in cursor.fetchall()]
    
    total = len(all_ids)
    print(f"Всего вопросов: {total}")
    
    # Распределяем по процентам
    easy_count = int(total * 0.20)    # 20% → EASY
    medium_count = int(total * 0.50)  # 50% → MEDIUM
    # Остальные → HARD (30%)
    
    print(f"Распределение:")
    print(f"  EASY: {easy_count} вопросов (20%)")
    print(f"  MEDIUM: {medium_count} вопросов (50%)")
    print(f"  HARD: {total - easy_count - medium_count} вопросов (30%)")
    
    updated = 0
    
    for i, q_id in enumerate(all_ids):
        if i < easy_count:
            difficulty = 'EASY'
        elif i < easy_count + medium_count:
            difficulty = 'MEDIUM'
        else:
            difficulty = 'HARD'
        
        cursor.execute(
            "UPDATE questions SET difficulty = ? WHERE id = ?",
            (difficulty, q_id)
        )
        updated += 1
        
        if updated % 500 == 0:
            print(f"  Обновлено {updated}...")
    
    conn.commit()
    
    # Проверка результата
    print("\nРезультат:")
    cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty ORDER BY difficulty")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()
    print(f"\nOK Обновлено: {updated} вопросов")

if __name__ == "__main__":
    fix_hard_difficulty()
