"""Импорт вопросов по истории из JSON в базу данных."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from models import Question, QuestionCategory, DifficultyLevel


async def import_history_questions(json_path: str = "data/generated/history_questions.json"):
    """Импортирует вопросы по истории в базу данных."""
    
    # Создаем подключение к БД
    engine = create_async_engine("sqlite+aiosqlite:///quiz_bot.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Загружаем вопросы
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Загружено {len(questions)} вопросов из {json_path}")
    
    # Статистика
    imported = 0
    skipped = 0
    errors = 0
    
    async with async_session() as session:
        for idx, q in enumerate(questions):
            try:
                # Проверяем на дубликаты по тексту вопроса
                result = await session.execute(
                    select(Question).where(Question.text == q['text'])
                )
                if result.scalar_one_or_none():
                    skipped += 1
                    continue
                
                # Определяем сложность
                try:
                    difficulty = DifficultyLevel[q['difficulty']]
                except KeyError:
                    difficulty = DifficultyLevel.MEDIUM
                
                # Создаем вопрос
                question = Question(
                    text=q['text'],
                    correct_answer=q['correct_answer'],
                    wrong_answers=q['wrong_answers'],
                    category=QuestionCategory.HISTORY,
                    difficulty=difficulty,
                    source='RuBQ_2.0'
                )
                
                session.add(question)
                imported += 1
                
                if imported % 50 == 0:
                    await session.commit()
                    print(f"  Импортировано {imported}...")
                
            except Exception as e:
                print(f"  Ошибка при импорте вопроса {idx}: {e}")
                errors += 1
                continue
        
        # Финальный коммит
        await session.commit()
    
    # Получаем статистику
    async with async_session() as session:
        total = await session.execute(select(func.count()).select_from(Question))
        total_count = total.scalar()
        
        history = await session.execute(
            select(func.count()).select_from(Question).where(Question.category == QuestionCategory.HISTORY)
        )
        history_count = history.scalar()
    
    print("\n" + "=" * 60)
    print("ИМПОРТ ЗАВЕРШЕН")
    print("=" * 60)
    print(f"Всего вопросов в файле: {len(questions)}")
    print(f"Импортировано: {imported}")
    print(f"Пропущено (дубликаты): {skipped}")
    print(f"Ошибок: {errors}")
    print(f"Всего вопросов в БД: {total_count}")
    print(f"Всего вопросов по истории: {history_count}")
    print("=" * 60)
    
    await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Импорт вопросов по истории в БД")
    print("=" * 60)
    
    asyncio.run(import_history_questions())
