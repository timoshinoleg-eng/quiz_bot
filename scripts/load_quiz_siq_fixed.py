# scripts/load_quiz_siq_fixed.py
"""
Загрузка вопросов из датасета Quiz SIQ Russian.
Исправленная версия для правильной схемы БД.
"""

import asyncio
import pandas as pd
import json
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Question  # Импортируем модель

async def load_quiz_siq(dataset_path: str = "quiz-siq/data/train-00000-of-00001.parquet"):
    """Загрузка вопросов из Quiz SIQ."""
    
    database_url = "sqlite+aiosqlite:///quiz_bot.db"
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print(f"Загрузка вопросов из Quiz SIQ: {dataset_path}")
    
    # Проверяем существование файла
    if not Path(dataset_path).exists():
        print(f"❌ Файл не найден: {dataset_path}")
        return
    
    # Читаем parquet файл
    df = pd.read_parquet(dataset_path)
    print(f"Найдено {len(df)} вопросов в датасете")
    
    questions_loaded = 0
    questions_skipped = 0
    
    async with async_session() as session:
        for idx, row in df.iterrows():
            try:
                # Извлекаем данные (адаптируйте под реальную структуру датасета)
                question_text = str(row.get('question', row.get('text', row.get('question_text', '')))).strip()
                correct_answer = str(row.get('answer', row.get('correct_answer', row.get('correct', '')))).strip()
                
                # Пропускаем пустые вопросы
                if not question_text or not correct_answer:
                    questions_skipped += 1
                    continue
                
                # Проверяем дубликаты
                existing = await session.execute(
                    select(Question).where(Question.text == question_text)
                )
                
                if existing.scalar_one_or_none():
                    questions_skipped += 1
                    continue
                
                # Получаем варианты ответов если есть
                wrong_answers = []
                options = row.get('options', row.get('wrong_answers', []))
                if isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except:
                        options = []
                
                wrong_answers = [opt for opt in options if opt != correct_answer][:3]
                
                # Дополняем до 3 неправильных ответов
                while len(wrong_answers) < 3:
                    wrong_answers.append(f"Вариант {len(wrong_answers) + 1}")
                
                # Определяем категорию
                category = str(row.get('category', row.get('topic', 'GENERAL'))).upper()[:100]
                if not category or category == 'nan':
                    category = 'GENERAL'
                
                # Определяем сложность
                difficulty_raw = str(row.get('difficulty', row.get('level', 'MEDIUM'))).lower()
                difficulty_map = {
                    'easy': 'EASY',
                    'medium': 'MEDIUM',
                    'hard': 'HARD',
                    'simple': 'EASY',
                    'normal': 'MEDIUM'
                }
                difficulty = difficulty_map.get(difficulty_raw, 'MEDIUM')
                
                # Создаём вопрос
                question = Question(
                    text=question_text,
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
                    print(f"Загружено {questions_loaded} вопросов...")
                
            except Exception as e:
                print(f"Ошибка при загрузке вопроса {idx}: {e}")
                questions_skipped += 1
                continue
        
        # Финальный коммит
        await session.commit()
    
    await engine.dispose()
    
    print(f"\n=== ИТОГО ===")
    print(f"✅ Загружено: {questions_loaded}")
    print(f"⚠️ Пропущено: {questions_skipped}")

if __name__ == "__main__":
    asyncio.run(load_quiz_siq())