"""SQLAlchemy модели для базы данных MAX-Квиз (MVP - одиночный режим)."""
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean,
    DateTime, ForeignKey, Text, Enum, JSON, Float
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class DifficultyLevel(str, enum.Enum):
    """Уровни сложности вопросов."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionCategory(str, enum.Enum):
    """Категории вопросов."""
    HISTORY = "history"
    SCIENCE = "science"
    ART = "art"
    SPORT = "sport"
    GEOGRAPHY = "geography"
    ENTERTAINMENT = "entertainment"
    GENERAL = "general"


class GameStatus(str, enum.Enum):
    """Статусы игры."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    # ИСПРАВЛЕНО: id - primary key без autoincrement для user_id
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    # Статистика
    score_total = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)

    # FSM состояние
    current_state = Column(String(50), nullable=True)
    state_data = Column(JSON, default=dict)

    # Premium
    premium_until = Column(DateTime, nullable=True)

    # Streaks
    daily_streak = Column(Integer, default=0)
    last_played = Column(DateTime, nullable=True)

    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Отношения (УПРОЩЕНО: удалены duels)
    games = relationship("Game", back_populates="user", lazy="dynamic")


class Question(Base):
    """Модель вопроса."""
    __tablename__ = "questions"

    # ИСПРАВЛЕНО: autoincrement=True для SQLite совместимости
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    category = Column(Enum(QuestionCategory), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)

    # Ответы
    correct_answer = Column(Text, nullable=False)
    wrong_answers = Column(JSON, nullable=False)
    explanation = Column(Text, nullable=True)

    # Метаданные источника
    source = Column(String(50), nullable=False)
    source_id = Column(String(100), nullable=True)

    # Статистика использования
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    correct_rate = Column(Float, default=0.0)

    created_at = Column(DateTime, default=func.now())


class Game(Base):
    """Модель игровой сессии (одиночный режим)."""
    __tablename__ = "games"

    # ИСПРАВЛЕНО: autoincrement=True для SQLite совместимости
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)

    # Настройки игры
    category = Column(Enum(QuestionCategory), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    question_count = Column(Integer, default=10)

    # Состояние игры
    status = Column(Enum(GameStatus), default=GameStatus.IN_PROGRESS)
    current_question_index = Column(Integer, default=0)
    score = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    lives_remaining = Column(Integer, default=3)

    # Временные метки
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Отношения (УПРОЩЕНО: удалены questions через GameQuestion)
    user = relationship("User", back_populates="games")


class AnalyticsEvent(Base):
    """Модель для аналитических событий."""
    __tablename__ = "analytics_events"

    # ИСПРАВЛЕНО: autoincrement=True для SQLite совместимости
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=func.now())


# УДАЛЕНО: Duel, Payment, DailyStreak - для MVP не нужны
# УДАЛЕНО: GameQuestion - связующая таблица для дуэлей, не нужна для одиночного режима
