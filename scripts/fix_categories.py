# scripts/fix_categories.py
"""
Нормализация категорий и сложности в БД.
Приводит все категории к формату, который ожидает бот.
"""

import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

conn = sqlite3.connect('quiz_bot.db')
cursor = conn.cursor()

print("=== Нормализация категорий ===")

# Маппинг категорий (приводим к UPPER_CASE)
category_mapping = {
    'science': 'SCIENCE',
    'наука': 'SCIENCE',
    'art': 'ART',
    'искусство': 'ART',
    'культура': 'ART',
    'history': 'HISTORY',
    'история': 'HISTORY',
    'geography': 'GEOGRAPHY',
    'география': 'GEOGRAPHY',
    'sport': 'SPORT',
    'спорт': 'SPORT',
    'facts': 'FACTS',
    'факты': 'FACTS',
    'общее': 'GENERAL',
    'general': 'GENERAL',
}

# Обновляем категории
for old_cat, new_cat in category_mapping.items():
    cursor.execute(
        "UPDATE questions SET category = ? WHERE UPPER(category) = ?",
        (new_cat, old_cat.upper())
    )
    updated = cursor.rowcount
    if updated > 0:
        print(f"  {old_cat} → {new_cat}: {updated} вопросов")

print("\n=== Нормализация сложности ===")

# Маппинг сложности
difficulty_mapping = {
    'easy': 'EASY',
    'легко': 'EASY',
    'лёгко': 'EASY',
    'простой': 'EASY',
    'medium': 'MEDIUM',
    'средне': 'MEDIUM',
    'средний': 'MEDIUM',
    'нормально': 'MEDIUM',
    'hard': 'HARD',
    'сложно': 'HARD',
    'сложный': 'HARD',
    'тяжело': 'HARD',
}

for old_diff, new_diff in difficulty_mapping.items():
    cursor.execute(
        "UPDATE questions SET difficulty = ? WHERE UPPER(difficulty) = ?",
        (new_diff, old_diff.upper())
    )
    updated = cursor.rowcount
    if updated > 0:
        print(f"  {old_diff} → {new_diff}: {updated} вопросов")

# Для вопросов без сложности ставим MEDIUM
cursor.execute(
    "UPDATE questions SET difficulty = 'MEDIUM' WHERE difficulty IS NULL OR difficulty = ''"
)
print(f"\n  Без сложности → MEDIUM: {cursor.rowcount} вопросов")

conn.commit()

# Финальная статистика
print("\n=== ИТОГО ===")
print("Категории:")
for row in cursor.execute('SELECT category, COUNT(*) FROM questions GROUP BY category ORDER BY COUNT(*) DESC'):
    print(f"  {row[0]}: {row[1]}")

print("\nСложность:")
for row in cursor.execute('SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty'):
    print(f"  {row[0]}: {row[1]}")

total = cursor.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
print(f"\n✅ Всего вопросов: {total}")

conn.close()