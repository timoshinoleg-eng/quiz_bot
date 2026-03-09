"""Импорт вопросов из словарей в базу данных."""
import json
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_db, close_db, db_manager


async def import_questions(json_path: str = "data/dictionary_questions.json"):
    """Импортирует вопросы из JSON в базу данных."""
    
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
    
    for q in questions:
        try:
            # Проверяем, существует ли такой вопрос
            existing = await db_manager.get_question_by_text(q['text'])
            if existing:
                print(f"  Skipping (exists): {q['text'][:50]}...")
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
            print(f"  Imported: {q['text'][:50]}...")
            imported += 1
            
        except Exception as e:
            print(f"  Error importing: {e}")
            errors += 1
    
    print("\n" + "=" * 60)
    print("Import Summary:")
    print(f"  Imported: {imported}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print("=" * 60)
    
    # Закрываем соединение
    await close_db()


if __name__ == "__main__":
    print("=" * 60)
    print("Dictionary Questions Importer")
    print("=" * 60)
    
    asyncio.run(import_questions())
