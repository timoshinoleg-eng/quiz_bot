"""
Загрузка переведённых вопросов OpenTDB в базу данных.
"""
import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

sys.path.insert(0, str(Path(__file__).parent.parent))
from models import Question, QuestionCategory, DifficultyLevel


async def load_translated_questions(
    input_path: str = "data/generated/opentdb_questions_ru.json",
    database_url: str = "sqlite+aiosqlite:///quiz_bot.db"
):
    """Загрузка переведённых вопросов в БД."""
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Загрузка вопросов
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Загрузка {len(questions)} вопросов в БД...")
    
    loaded = 0
    skipped = 0
    errors = 0
    
    async with async_session() as session:
        for q in questions:
            try:
                # Проверка на дубликаты
                existing = await session.execute(
                    select(Question).where(Question.text == q['text'])
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue
                
                # Маппинг категории
                category_map = {
                    'GENERAL': QuestionCategory.GENERAL,
                    'HISTORY': QuestionCategory.HISTORY,
                    'SCIENCE': QuestionCategory.SCIENCE,
                    'ART': QuestionCategory.ART,
                    'SPORT': QuestionCategory.SPORT,
                    'GEOGRAPHY': QuestionCategory.GEOGRAPHY,
                }
                category = category_map.get(
                    q.get('category', 'GENERAL'),
                    QuestionCategory.GENERAL
                )
                
                # Маппинг сложности
                difficulty_map = {
                    'EASY': DifficultyLevel.EASY,
                    'MEDIUM': DifficultyLevel.MEDIUM,
                    'HARD': DifficultyLevel.HARD
                }
                difficulty = difficulty_map.get(
                    q.get('difficulty', 'MEDIUM'),
                    DifficultyLevel.MEDIUM
                )
                
                # Создание вопроса
                question = Question(
                    text=q['text'],
                    correct_answer=q['correct_answer'],
                    wrong_answers=json.dumps(q['wrong_answers'], ensure_ascii=False),
                    category=category,
                    difficulty=difficulty,
                    source=q.get('source', 'OpenTDB'),
                    is_active=True
                )
                
                session.add(question)
                loaded += 1
                
                if loaded % 100 == 0:
                    await session.commit()
                    print(f"  Загружено {loaded} вопросов...")
                    
            except Exception as e:
                print(f"  Ошибка загрузки: {e}")
                errors += 1
                continue
        
        await session.commit()
    
    # Статистика
    async with async_session() as session:
        total = await session.execute(select(func.count()).select_from(Question))
        total_count = total.scalar()
    
    await engine.dispose()
    
    print(f"\nЗагружено: {loaded}")
    print(f"Пропущено (дубликаты): {skipped}")
    print(f"Ошибок: {errors}")
    print(f"Всего вопросов в БД: {total_count}")


if __name__ == "__main__":
    print("=" * 60)
    print("Загрузка переведённых вопросов OpenTDB")
    print("=" * 60)
    
    asyncio.run(load_translated_questions())
