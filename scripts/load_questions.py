#!/usr/bin/env python3
"""Скрипт для загрузки вопросов в базу данных.

Поддерживает загрузку из:
- RuBQ JSON файла
- Open Trivia Database API

Usage:
    python load_questions.py --source rubq --file data/rubq.json
    python load_questions.py --source opentdb --amount 100
    python load_questions.py --source opentdb --amount 50 --category 9 --difficulty medium
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from db import init_db, close_db
from questions import question_loader
from content.validator import batch_validator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def load_from_rubq(file_path: str, limit: int = None) -> None:
    """Загружает вопросы из RuBQ JSON файла.
    
    Args:
        file_path: Путь к JSON файлу
        limit: Ограничение количества вопросов
    """
    logger.info(f"Loading questions from RuBQ: {file_path}")
    
    stats = await question_loader.load_from_rubq(file_path, limit)
    
    logger.info(f"RuBQ loading complete:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Loaded: {stats['loaded']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Skipped: {stats.get('skipped', 0)}")


async def load_from_opentdb(
    amount: int = 50,
    category: int = None,
    difficulty: str = None
) -> None:
    """Загружает вопросы из Open Trivia Database.
    
    Args:
        amount: Количество вопросов
        category: ID категории
        difficulty: Сложность (easy, medium, hard)
    """
    logger.info(f"Loading questions from OpenTDB: amount={amount}")
    
    stats = await question_loader.load_from_opentdb(amount, category, difficulty)
    
    logger.info(f"OpenTDB loading complete:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Loaded: {stats['loaded']}")
    logger.info(f"  Errors: {stats['errors']}")


async def validate_questions_file(file_path: str) -> None:
    """Валидирует файл с вопросами без загрузки.
    
    Args:
        file_path: Путь к JSON файлу
    """
    logger.info(f"Validating questions file: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data if isinstance(data, list) else data.get("questions", [])
    
    logger.info(f"Found {len(questions)} questions")
    
    results = await batch_validator.validate_batch(questions)
    
    logger.info(f"Validation results:")
    logger.info(f"  Total: {results['total']}")
    logger.info(f"  Valid: {results['valid']}")
    logger.info(f"  Invalid: {results['invalid']}")
    logger.info(f"  Errors: {results['errors']}")
    logger.info(f"  Warnings: {results['warnings']}")
    
    # Показываем детали
    for detail in results['details']:
        if not detail['is_valid']:
            logger.warning(
                f"Question {detail['index']}: "
                f"score={detail['score']}, "
                f"errors={detail['errors']}, "
                f"warnings={detail['warnings']}"
            )


async def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Load questions into MAX-Квiz database"
    )
    
    parser.add_argument(
        "--source",
        choices=["rubq", "opentdb", "validate"],
        required=True,
        help="Source of questions"
    )
    
    parser.add_argument(
        "--file",
        help="Path to JSON file (for rubq source)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of questions to load"
    )
    
    parser.add_argument(
        "--amount",
        type=int,
        default=50,
        help="Number of questions to fetch from OpenTDB"
    )
    
    parser.add_argument(
        "--category",
        type=int,
        help="Category ID for OpenTDB (9=General, 10=Books, etc.)"
    )
    
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="Difficulty level for OpenTDB"
    )
    
    args = parser.parse_args()
    
    # Инициализируем БД
    await init_db()
    
    try:
        if args.source == "rubq":
            if not args.file:
                logger.error("--file is required for rubq source")
                sys.exit(1)
            
            await load_from_rubq(args.file, args.limit)
        
        elif args.source == "opentdb":
            await load_from_opentdb(args.amount, args.category, args.difficulty)
        
        elif args.source == "validate":
            if not args.file:
                logger.error("--file is required for validate source")
                sys.exit(1)
            
            await validate_questions_file(args.file)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    
    finally:
        await question_loader.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
