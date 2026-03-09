# scripts/load_questions.py
"""
Загрузка вопросов из датасетов в базу данных quiz_bot.
"""

import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
import logging

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Question, DifficultyLevel
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionLoader:
    """Загрузчик вопросов из различных датасетов."""
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.stats = {
            "loaded": 0,
            "skipped": 0,
            "errors": 0
        }
    
    async def load_from_rubq(self, dataset_path: str):
        """Загрузка из RuBQ 2.0."""
        try:
            import pandas as pd
            
            logger.info(f"Загрузка вопросов из RuBQ: {dataset_path}")
            
            # Загружаем все parquet файлы
            questions_loaded = 0
            
            # Ищем parquet файлы в папке data
            data_path = Path(dataset_path) / "data"
            if not data_path.exists():
                data_path = Path(dataset_path)
            
            for parquet_file in data_path.glob("*.parquet"):
                logger.info(f"Обработка файла: {parquet_file.name}")
                df = pd.read_parquet(parquet_file)
                
                async with self.async_session() as session:
                    for _, row in df.iterrows():
                        try:
                            question_text = row.get('question_text', '').strip()
                            answer_text = row.get('answer_text', '').strip()
                            tags = row.get('tags', 'Общее')
                            
                            if not question_text or not answer_text:
                                self.stats["skipped"] += 1
                                continue
                            
                            # Проверяем дубликаты
                            existing = await session.execute(
                                select(Question).where(
                                    Question.text == question_text
                                )
                            )
                            
                            if existing.scalar_one_or_none():
                                self.stats["skipped"] += 1
                                continue
                            
                            # Создаём вопрос с 3 неправильными ответами-заглушками
                            from models import QuestionCategory
                            
                            question = Question(
                                text=question_text,
                                correct_answer=answer_text,
                                wrong_answers=[
                                    "Вариант 1",
                                    "Вариант 2",
                                    "Вариант 3"
                                ],
                                category=QuestionCategory.GENERAL,
                                difficulty=DifficultyLevel.MEDIUM,
                                source='RuBQ 2.0'
                            )
                            
                            session.add(question)
                            questions_loaded += 1
                            self.stats["loaded"] += 1
                            
                            # Коммит каждые 100 вопросов
                            if questions_loaded % 100 == 0:
                                await session.commit()
                                logger.info(f"Загружено {questions_loaded} вопросов...")
                        
                        except Exception as e:
                            logger.error(f"Ошибка при загрузке вопроса: {e}")
                            self.stats["errors"] += 1
                            continue
                
                logger.info(f"Файл {parquet_file.name} обработан")
            
            # Финальный коммит
            async with self.async_session() as session:
                await session.commit()
            
            logger.info(f"✅ RuBQ: Загружено {questions_loaded} вопросов")
            
        except ImportError:
            logger.error("Требуется pandas: pip install pandas")
        except Exception as e:
            logger.error(f"Ошибка загрузки RuBQ: {e}")
    
    async def load_from_russian_facts(self, dataset_path: str):
        """Загрузка из Russian Facts QA."""
        try:
            logger.info(f"Загрузка вопросов из Russian Facts QA: {dataset_path}")
            
            questions_loaded = 0
            jsonl_file = Path(dataset_path) / "russian_facts_qa.jsonl"
            
            if not jsonl_file.exists():
                # Ищем альтернативные имена
                jsonl_file = Path(dataset_path) / "qa_dataset.jsonl"
            
            if not jsonl_file.exists():
                logger.error(f"Файл не найден: {jsonl_file}")
                return
            
            async with self.async_session() as session:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            
                            question_text = data.get('question', '').strip()
                            answer_text = data.get('answer', '').strip()
                            
                            if not question_text or not answer_text:
                                self.stats["skipped"] += 1
                                continue
                            
                            # Проверяем дубликаты
                            existing = await session.execute(
                                select(Question).where(
                                    Question.text == question_text
                                )
                            )
                            
                            if existing.scalar_one_or_none():
                                self.stats["skipped"] += 1
                                continue
                            
                            from models import QuestionCategory
                            
                            question = Question(
                                text=question_text,
                                correct_answer=answer_text,
                                wrong_answers=[
                                    "Неверно 1",
                                    "Неверно 2",
                                    "Неверно 3"
                                ],
                                category=QuestionCategory.GENERAL,
                                difficulty=DifficultyLevel.MEDIUM,
                                source='Russian Facts QA'
                            )
                            
                            session.add(question)
                            questions_loaded += 1
                            self.stats["loaded"] += 1
                            
                            # Коммит каждые 100 вопросов
                            if questions_loaded % 100 == 0:
                                await session.commit()
                                logger.info(f"Загружено {questions_loaded} вопросов...")
                        
                        except Exception as e:
                            logger.error(f"Ошибка при загрузке вопроса: {e}")
                            self.stats["errors"] += 1
                            continue
                
                await session.commit()
            
            logger.info(f"✅ Russian Facts QA: Загружено {questions_loaded} вопросов")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Russian Facts QA: {e}")
    
    async def get_total_questions(self) -> int:
        """Получить общее количество вопросов в БД."""
        async with self.async_session() as session:
            result = await session.execute(select(func.count()).select_from(Question))
            return result.scalar()
    
    async def close(self):
        await self.engine.dispose()


async def main():
    """Основной скрипт загрузки."""
    # Используем SQLite как в основном боте
    database_url = "sqlite+aiosqlite:///quiz_bot.db"
    
    loader = QuestionLoader(database_url)
    
    try:
        # Проверяем текущее количество вопросов
        total_before = await loader.get_total_questions()
        logger.info(f"Вопросов в БД до загрузки: {total_before}")
        
        # Загружаем из RuBQ 2.0
        rubq_path = Path("RuBQ_2.0")
        if rubq_path.exists():
            await loader.load_from_rubq(str(rubq_path))
        else:
            logger.warning(f"Папка RuBQ_2.0 не найдена: {rubq_path}")
        
        # Загружаем из Russian Facts QA
        facts_path = Path("russian-facts-qa")
        if facts_path.exists():
            await loader.load_from_russian_facts(str(facts_path))
        else:
            logger.warning(f"Папка russian-facts-qa не найдена: {facts_path}")
        
        # Финальная статистика
        total_after = await loader.get_total_questions()
        
        logger.info("=" * 50)
        logger.info("✅ Загрузка завершена!")
        logger.info(f"   Загружено вопросов: {loader.stats['loaded']}")
        logger.info(f"   Пропущено (дубликаты): {loader.stats['skipped']}")
        logger.info(f"   Ошибок: {loader.stats['errors']}")
        logger.info(f"   Всего вопросов в БД: {total_after}")
        logger.info("=" * 50)
        
    finally:
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main())