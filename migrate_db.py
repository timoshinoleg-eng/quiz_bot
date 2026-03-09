#!/usr/bin/env python3
"""
Скрипт миграции БД для исправления схемы games.

Использование:
    python migrate_db.py
"""

import asyncio
import logging
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    database_url = "sqlite+aiosqlite:///quiz_bot.db"
    engine = create_async_engine(database_url)
    
    async with engine.begin() as conn:
        # Пересоздать таблицу questions
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
        ))
        
        if result.fetchone():
            logger.info("⚠️ Таблица questions существует. Пересоздание...")
            await conn.execute(text("DROP TABLE questions"))
            logger.info("✅ Таблица questions удалена")
        
        await conn.execute(text("""
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category VARCHAR(100) NOT NULL,
                difficulty VARCHAR(20) NOT NULL,
                correct_answer TEXT NOT NULL,
                wrong_answers JSON NOT NULL,
                explanation TEXT,
                source VARCHAR(50) NOT NULL,
                source_id VARCHAR(100),
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                correct_rate FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        logger.info("✅ Таблица questions создана с правильной схемой")
        
        # Проверить существование таблицы games
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        ))
        
        if result.fetchone():
            logger.info("⚠️ Таблица games существует. Пересоздание...")
            await conn.execute(text("DROP TABLE games"))
            logger.info("✅ Таблица games удалена")
        
        # Пересоздать с правильной схемой
        await conn.execute(text("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT NOT NULL,
                category VARCHAR(100),
                difficulty VARCHAR(20),
                question_count INTEGER DEFAULT 10,
                status VARCHAR(20) DEFAULT 'in_progress',
                current_question_index INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                lives_remaining INTEGER DEFAULT 3,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        logger.info("✅ Таблица games создана с правильной схемой")
        
        # Проверить существование таблицы analytics_events
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='analytics_events'"
        ))
        
        if not result.fetchone():
            logger.info("⚠️ Таблица analytics_events не существует. Создание...")
            await conn.execute(text("""
                CREATE TABLE analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT,
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            logger.info("✅ Таблица analytics_events создана")
    
    await engine.dispose()
    logger.info("✅ Миграция завершена. Перезапустите бота.")

if __name__ == "__main__":
    asyncio.run(migrate())
