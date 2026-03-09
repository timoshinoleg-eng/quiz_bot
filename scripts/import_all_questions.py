"""Импорт всех сгенерированных вопросов в базу данных."""
import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_db, close_db, db_manager


async def import_all_questions(json_path: str = "data/all_generated_questions.json"):
    """Импортирует все вопросы из JSON в базу данных."""
    
    # Инициализируем БД
    await init_db()
    
    # Загружаем вопросы
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Loaded {len(questions)} questions from {json_path}")
    
    # Статистика
    imported = 0
    skipped = 0
    errors = 0
    
    # Статистика по категориям
    category_stats = {}
    
    for q in questions:
        try:
            # Проверяем, существует ли такой вопрос
            existing = await db_manager.get_question_by_text(q['text'])
            if existing:
                skipped += 1
                continue
            
            # Добавляем вопрос
            await db_manager.add_question(
                text=q['text'],
                correct_answer=q['correct_answer'],
                wrong_answers=q['wrong_answers'],
                category=q['category'],
                difficulty=q['difficulty']
            )
            imported += 1
            
            # Считаем по категориям
            cat = q['category']
            category_stats[cat] = category_stats.get(cat, 0) + 1
            
            if imported % 50 == 0:
                print(f"  Imported {imported}...")
            
        except Exception as e:
            print(f"  Error: {e}")
            errors += 1
    
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Total: {len(questions)}")
    print(f"Imported: {imported}")
    print(f"Skipped (exists): {skipped}")
    print(f"Errors: {errors}")
    
    print("\nBy category:")
    for cat, count in sorted(category_stats.items()):
        print(f"  {cat}: {count}")
    
    print("=" * 60)
    
    # Закрываем соединение
    await close_db()


if __name__ == "__main__":
    print("=" * 60)
    print("All Questions Importer")
    print("=" * 60)
    
    asyncio.run(import_all_questions())
