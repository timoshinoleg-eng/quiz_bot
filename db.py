"""Асинхронная работа с базой данных.

Этот модуль предоставляет асинхронные функции для работы с БД,
используя SQLAlchemy с asyncpg драйвером.

Example:
    >>> from db import get_db, init_db
    >>> await init_db()
    >>> async with get_db() as db:
    ...     user = await db.get_user(123456)
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Any, Dict

from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, AsyncEngine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, insert, delete, func

from config import settings
from models import (
    Base, User, Question, Game, GameQuestion, Duel,
    Payment, AnalyticsEvent, DailyStreak,
    QuestionCategory, DifficultyLevel, GameStatus
)


logger = logging.getLogger(__name__)

# Глобальные переменные для engine и session
_engine: Optional[AsyncEngine] = None
_async_session: Optional[sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Получает или создаёт AsyncEngine.
    
    Returns:
        AsyncEngine: Асинхронный движок SQLAlchemy
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE.url,
            echo=settings.DATABASE.echo,
            pool_size=settings.DATABASE.pool_size,
            max_overflow=settings.DATABASE.max_overflow,
            pool_pre_ping=True,
        )
    return _engine


def get_session_maker() -> sessionmaker:
    """Получает или создаёт фабрику сессий.
    
    Returns:
        sessionmaker: Фабрика асинхронных сессий
    """
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
    """Контекстный менеджер для получения сессии БД.
    
    Yields:
        AsyncSession: Асинхронная сессия БД
        
    Example:
        >>> async with get_db() as db:
        ...     result = await db.execute(select(User))
    """
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
    """Инициализирует базу данных (создаёт таблицы).
    
    Вызывается при первом запуске приложения.
    """
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
    """Менеджер для работы с базой данных.
    
    Предоставляет высокоуровневые методы для CRUD операций.
    """
    
    @staticmethod
    async def get_or_create_user(
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Получает или создаёт пользователя.
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            first_name: Имя
            last_name: Фамилия
            
        Returns:
            User: Объект пользователя
        """
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
    async def update_user_state(
        user_id: int,
        state: Optional[str],
        state_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обновляет состояние пользователя (FSM).
        
        Args:
            user_id: ID пользователя
            state: Новое состояние
            state_data: Данные состояния
        """
        async with get_db() as db:
            update_data = {"current_state": state}
            if state_data is not None:
                update_data["state_data"] = state_data
            
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
    
    @staticmethod
    async def get_user_state(user_id: int) -> tuple:
        """Получает состояние пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            tuple: (state, state_data)
        """
        async with get_db() as db:
            result = await db.execute(
                select(User.current_state, User.state_data)
                .where(User.id == user_id)
            )
            row = result.fetchone()
            return (row[0], row[1]) if row else (None, {})
    
    @staticmethod
    async def is_premium(user_id: int) -> bool:
        """Проверяет, есть ли у пользователя Premium.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если Premium активен
        """
        async with get_db() as db:
            result = await db.execute(
                select(User.premium_until)
                .where(User.id == user_id)
            )
            premium_until = result.scalar_one_or_none()
            
            if premium_until is None:
                return False
            
            from datetime import datetime
            return premium_until > datetime.utcnow()
    
    @staticmethod
    async def get_random_questions(
        category: QuestionCategory,
        difficulty: DifficultyLevel,
        count: int = 10
    ) -> List[Question]:
        """Получает случайные вопросы по категории и сложности.
        
        Args:
            category: Категория вопросов
            difficulty: Уровень сложности
            count: Количество вопросов
            
        Returns:
            List[Question]: Список вопросов
        """
        async with get_db() as db:
            result = await db.execute(
                select(Question)
                .where(
                    Question.category == category,
                    Question.difficulty == difficulty,
                    Question.is_active == True
                )
                .order_by(func.random())
                .limit(count)
            )
            return result.scalars().all()
    
    @staticmethod
    async def create_game(
        user_id: int,
        category: QuestionCategory,
        difficulty: DifficultyLevel,
        question_count: int
    ) -> Game:
        """Создаёт новую игру.
        
        Args:
            user_id: ID пользователя
            category: Категория
            difficulty: Сложность
            question_count: Количество вопросов
            
        Returns:
            Game: Созданная игра
        """
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
    async def get_game(game_id: int) -> Optional[Game]:
        """Получает игру по ID.
        
        Args:
            game_id: ID игры
            
        Returns:
            Optional[Game]: Игра или None
        """
        async with get_db() as db:
            result = await db.execute(
                select(Game).where(Game.id == game_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_game_score(
        game_id: int,
        points: int,
        is_correct: bool
    ) -> None:
        """Обновляет счёт игры.
        
        Args:
            game_id: ID игры
            points: Очки за ответ
            is_correct: Правильный ли ответ
        """
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
        """Завершает игру.
        
        Args:
            game_id: ID игры
        """
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if game:
                game.status = GameStatus.COMPLETED
                from datetime import datetime
                game.completed_at = datetime.utcnow()
                
                # Обновляем статистику пользователя
                user = await db.get(User, game.user_id)
                if user:
                    user.score_total += game.score
                    user.games_played += 1
    
    @staticmethod
    async def create_duel(
        player1_id: int,
        category: QuestionCategory,
        question_count: int = 5
    ) -> Duel:
        """Создаёт новую дуэль.
        
        Args:
            player1_id: ID создателя
            category: Категория
            question_count: Количество вопросов
            
        Returns:
            Duel: Созданная дуэль
        """
        async with get_db() as db:
            duel = Duel(
                player1_id=player1_id,
                category=category,
                question_count=question_count
            )
            db.add(duel)
            await db.commit()
            await db.refresh(duel)
            return duel
    
    @staticmethod
    async def join_duel(duel_id: int, player2_id: int) -> bool:
        """Присоединяет второго игрока к дуэли.
        
        Args:
            duel_id: ID дуэли
            player2_id: ID присоединяющегося игрока
            
        Returns:
            bool: True если успешно
        """
        async with get_db() as db:
            duel = await db.get(Duel, duel_id)
            if duel and duel.player2_id is None:
                duel.player2_id = player2_id
                duel.status = "in_progress"
                from datetime import datetime
                duel.started_at = datetime.utcnow()
                return True
            return False
    
    @staticmethod
    async def log_event(
        event_type: str,
        user_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирует аналитическое событие.
        
        Args:
            event_type: Тип события
            user_id: ID пользователя
            event_data: Данные события
        """
        if not settings.FEATURES.enable_analytics:
            return
            
        async with get_db() as db:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data or {}
            )
            db.add(event)


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()
