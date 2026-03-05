"""Асинхронная работа с базой данных (MVP - упрощенная версия)."""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, AsyncEngine
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import select, update, insert, delete, func

logger = logging.getLogger(__name__)

# Создаём Base локально если не импортируется из models
try:
    # ИСПРАВЛЕНО: удалены Duel, Payment, DailyStreak, GameQuestion
    from models import Base, User, Question, Game, AnalyticsEvent
    from models import QuestionCategory, DifficultyLevel, GameStatus
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Models not available: {e}")
    MODELS_AVAILABLE = False
    Base = declarative_base()
    
    class User: pass
    class Question: pass
    class Game: pass
    
    class QuestionCategory:
        HISTORY = "history"
        SCIENCE = "science"
        SPORT = "sport"
        GEOGRAPHY = "geography"
        ART = "art"
        ENTERTAINMENT = "entertainment"
    
    class DifficultyLevel:
        EASY = "easy"
        MEDIUM = "medium"
        HARD = "hard"
    
    class GameStatus:
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        ABANDONED = "abandoned"

# Глобальные переменные для engine и session
_engine: Optional[AsyncEngine] = None
_async_session: Optional[sessionmaker] = None


def get_database_url() -> str:
    """Получает URL базы данных из окружения."""
    return os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///quiz_bot.db')


def get_engine() -> AsyncEngine:
    """Получает или создаёт AsyncEngine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        
        # Поддержка SQLite и PostgreSQL
        if database_url.startswith("sqlite"):
            _engine = create_async_engine(
                database_url,
                echo=os.getenv('DEBUG', 'false').lower() == 'true',
                connect_args={"check_same_thread": False}
            )
        else:
            _engine = create_async_engine(
                database_url,
                echo=os.getenv('DEBUG', 'false').lower() == 'true',
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )
    
    return _engine


def get_session_maker() -> sessionmaker:
    """Получает или создаёт фабрику сессий."""
    global _async_session
    if _async_session is None:
        _async_session = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Контекстный менеджер для получения сессии БД."""
    session = get_session_maker()()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Инициализирует базу данных (создаёт таблицы)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Закрывает соединение с базой данных."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed")


class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    @staticmethod
    async def get_or_create_user(
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Any:
        """Получает или создаёт пользователя."""
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user is None:
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                db.add(user)
                await db.commit()
                logger.info(f"Created new user: {user_id}")
            
            return user

    @staticmethod
    async def is_premium(user_id: int) -> bool:
        """Проверяет, есть ли у пользователя Premium."""
        async with get_db() as db:
            result = await db.execute(
                select(User.premium_until).where(User.id == user_id)
            )
            premium_until = result.scalar_one_or_none()
            
            if premium_until is None:
                return False
            
            from datetime import datetime
            return premium_until > datetime.utcnow()

    @staticmethod
    async def log_event(
        event_type: str,
        user_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирует аналитическое событие."""
        # ИСПРАВЛЕНО: отключено для MVP - избегаем ошибок с autoincrement в SQLite
        logger.debug(f"Event logged: {event_type}, user: {user_id}")
        return
        
        # Старый код (закомментирован для включения позже):
        # async with get_db() as db:
        #     event = AnalyticsEvent(
        #         user_id=user_id,
        #         event_type=event_type,
        #         event_data=event_data or {}
        #     )
        #     db.add(event)

    @staticmethod
    async def create_game(
        user_id: int,
        category: Any,
        difficulty: Any,
        question_count: int
    ) -> Any:
        """Создаёт новую игру."""
        async with get_db() as db:
            game = Game(
                user_id=user_id,
                category=category,
                difficulty=difficulty,
                question_count=question_count,
                lives_remaining=3
            )
            db.add(game)
            await db.commit()
            await db.refresh(game)
            return game

    @staticmethod
    async def get_game(game_id: int) -> Optional[Any]:
        """Получает игру по ID."""
        async with get_db() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def update_game_score(
        game_id: int,
        points: int,
        is_correct: bool
    ) -> None:
        """Обновляет счёт игры."""
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if game:
                game.score += points
                if is_correct:
                    game.correct_answers += 1
                else:
                    game.lives_remaining -= 1
                
                if game.lives_remaining <= 0:
                    game.status = GameStatus.ABANDONED
                    from datetime import datetime
                    game.completed_at = datetime.utcnow()

    @staticmethod
    async def complete_game(game_id: int) -> None:
        """Завершает игру."""
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if game:
                game.status = GameStatus.COMPLETED
                from datetime import datetime
                game.completed_at = datetime.utcnow()
                
                user = await db.get(User, game.user_id)
                if user:
                    user.score_total += game.score
                    user.games_played += 1

    @staticmethod
    async def update_user_state(
        user_id: int,
        state: Optional[str],
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обновляет состояние пользователя (FSM)."""
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if user:
                user.current_state = state
                user.state_data = data or {}
                await db.commit()
                logger.debug(f"Updated user {user_id} state: {state}")

    @staticmethod
    async def get_user_state(user_id: int) -> tuple:
        """Получает состояние пользователя.
        
        Returns:
            tuple: (state, data)
        """
        async with get_db() as db:
            result = await db.execute(
                select(User.current_state, User.state_data).where(User.id == user_id)
            )
            row = result.one_or_none()
            
            if row:
                return row[0], row[1] or {}
            return None, {}


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()
