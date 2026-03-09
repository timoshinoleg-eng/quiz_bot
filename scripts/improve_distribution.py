#!/usr/bin/env python3
"""
Улучшение распределения вопросов по категориям и сложности.
"""

import sqlite3
from pathlib import Path

def improve_distribution(database_path: str = "quiz_bot.db"):
    """Улучшение распределения вопросов."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    print("Анализ текущего распределения...")
    
    # Категории
    cursor.execute("SELECT category, COUNT(*) FROM questions GROUP BY category")
    categories = dict(cursor.fetchall())
    print(f"\nКатегории: {categories}")
    
    # Сложность
    cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty")
    difficulties = dict(cursor.fetchall())
    print(f"Сложность: {difficulties}")
    
    # Улучшение: перераспределить GENERAL вопросы
    print("\nПерераспределение GENERAL вопросов...")
    
    category_keywords = {
        'SCIENCE': ['наука', 'физика', 'химия', 'биология', 'космос', 'атом', 'энергия', 'планета'],
        'HISTORY': ['история', 'война', 'царь', 'революция', 'год', 'век', 'империя', 'битва'],
        'GEOGRAPHY': ['город', 'страна', 'река', 'море', 'столица', 'остров', 'континент', 'гора'],
        'ART': ['художник', 'картина', 'музыка', 'писатель', 'книга', 'фильм', 'театр', 'роман'],
        'SPORT': ['спорт', 'футбол', 'хоккей', 'олимпиада', 'чемпион', 'команда', 'игрок', 'матч'],
        'NATURE': ['животное', 'птица', 'растение', 'дерево', 'лес', 'природа', 'зверь'],
        'TECHNOLOGY': ['компьютер', 'интернет', 'программа', 'код', 'сайт', 'робот', 'технология'],
    }
    
    updated = 0
    
    # Получить GENERAL вопросы
    cursor.execute("SELECT id, text FROM questions WHERE category = 'GENERAL'")
    general_questions = cursor.fetchall()
    
    for q_id, text in general_questions:
        text_lower = text.lower()
        
        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                cursor.execute(
                    "UPDATE questions SET category = ? WHERE id = ?",
                    (category, q_id)
                )
                updated += 1
                break
    
    conn.commit()
    
    print(f"OK Перераспределено: {updated} вопросов из GENERAL")
    
    # Улучшение сложности
    print("\nУлучшение распределения сложности...")
    
    difficulty_keywords = {
        'EASY': ['прост', 'легк', 'известн', 'основн', 'популярн'],
        'HARD': ['сложн', 'трудн', 'редк', 'малоизвестн', 'запутан']
    }
    
    updated_difficulty = 0
    
    cursor.execute("SELECT id, text, difficulty FROM questions WHERE difficulty = 'MEDIUM'")
    medium_questions = cursor.fetchall()
    
    for q_id, text, _ in medium_questions:
        text_lower = text.lower()
        
        for difficulty, keywords in difficulty_keywords.items():
            if any(kw in text_lower for kw in keywords):
                cursor.execute(
                    "UPDATE questions SET difficulty = ? WHERE id = ?",
                    (difficulty, q_id)
                )
                updated_difficulty += 1
                break
    
    conn.commit()
    
    print(f"OK Обновлена сложность: {updated_difficulty} вопросов")
    
    # Финальная статистика
    print("\nФинальное распределение:")
    
    cursor.execute("SELECT category, COUNT(*) FROM questions GROUP BY category ORDER BY COUNT(*) DESC")
    print("\nКатегории:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.execute("SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty ORDER BY COUNT(*) DESC")
    print("\nСложность:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    improve_distribution()
