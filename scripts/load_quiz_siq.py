# scripts/load_quiz_siq.py
"""
Загрузка вопросов из датасета quiz-siq-russian в базу данных.
"""

import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import logging

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Question, QuestionDifficulty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_quiz_siq(dataset_path: str = "quiz-siq/data/train-00000-of-00001.parquet"):
    """Загрузка вопросов из Quiz SIQ Russian."""
    
    try:
        import pandas as pd
    except ImportError:
        logger.error("Требуется pandas: pip install pandas")
        return
    
    database_url = "sqlite+aiosqlite:///quiz_bot.db"
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info(f"Загрузка вопросов из Quiz SIQ: {dataset_path}")
    
    # Читаем parquet файл
    df = pd.read_parquet(dataset_path)
    logger.info(f"Найдено {len(df)} вопросов в датасете")
    
    questions_loaded = 0
    questions_skipped = 0
    
    async with async_session() as session:
        for idx, row in df.iterrows():
            try:
                # Извлекаем данные из строки
                question_text = str(row.get('question', '')).strip()
                correct_answer = str(row.get('answer', '')).strip()
                
                # Пропускаем пустые вопросы
                if not question_text or not correct_answer:
                    questions_skipped += 1
                    continue
                
                # Проверяем дубликаты
                existing = await session.execute(
                    select(Question).where(Question.question_text == question_text)
                )
                
                if existing.scalar_one_or_none():
                    questions_skipped += 1
                    continue
                
                # Создаём вопрос
                # Quiz SIQ обычно имеет multiple choice ответы
                options = row.get('options', [])
                if isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except:
                        options = []
                
                # Формируем неправильные ответы
                wrong_answers = [opt for opt in options if opt != correct_answer][:3]
                
                # Дополняем до 3 вариантов если нужно
                while len(wrong_answers) < 3:
                    wrong_answers.append(f"Вариант {len(wrong_answers) + 1}")
                
                # Определяем категорию
                category = str(row.get('category', row.get('topic', 'GENERAL'))).upper()[:100]
                if not category or category == 'nan':
                    category = 'GENERAL'
                
                # Определяем сложность
                difficulty_raw = str(row.get('difficulty', 'medium')).lower()
                difficulty_map = {
                    'easy': QuestionDifficulty.EASY,
                    'medium': QuestionDifficulty.MEDIUM,
                    'hard': QuestionDifficulty.HARD,
                    'simple': QuestionDifficulty.EASY,
                    'normal': QuestionDifficulty.MEDIUM
                }
                difficulty = difficulty_map.get(difficulty_raw, QuestionDifficulty.MEDIUM)
                
                question = Question(
                    question_text=question_text,
                    correct_answer=correct_answer,
                    wrong_answers=json.dumps(wrong_answers[:3]),
                    category=category,
                    difficulty=difficulty,
                    source='Quiz SIQ Russian',
                    is_active=True
                )
                
                session.add(question)
                questions_loaded += 1
                
                # Коммит каждые 100 вопросов
                if questions_loaded % 100 == 0:
                    await session.commit()
                    logger.info(f"Загружено {questions_loaded} вопросов...")
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке вопроса {idx}: {e}")
                questions_skipped += 1
                continue
        
        # Финальный коммит
        await session.commit()
    
    await engine.dispose()
    
    logger.info("=" * 50)
    logger.info("✅ Загрузка Quiz SIQ завершена!")
    logger.info(f"   Загружено вопросов: {questions_loaded}")
    logger.info(f"   Пропущено (дубликаты): {questions_skipped}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(load_quiz_siq())