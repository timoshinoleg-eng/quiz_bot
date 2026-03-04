"""SQLAlchemy модели для базы данных MAX-Квиз.

Этот модуль содержит все ORM модели для работы с базой данных.
Включает модели пользователей, вопросов, игр, дуэлей и аналитики.

Example:
    >>> from models import User, Question
    >>> user = User(id=123456, username="test_user")
"""

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
    SPORTS = "sports"
    GEOGRAPHY = "geography"
    ENTERTAINMENT = "entertainment"
    GENERAL = "general"


class GameStatus(str, enum.Enum):
    """Статусы игры."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DuelStatus(str, enum.Enum):
    """Статусы дуэли."""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class User(Base):
    """Модель пользователя.
    
    Attributes:
        id: Уникальный ID пользователя (Telegram/MAX ID)
        username: Имя пользователя
        first_name: Имя
        last_name: Фамилия
        score_total: Общий счёт
        games_played: Количество сыгранных игр
        games_won: Количество побед
        current_state: Текущее состояние FSM
        state_data: Данные состояния (JSON)
        premium_until: Дата окончания Premium
        daily_streak: Текущий streak
        last_played: Дата последней игры
        created_at: Дата регистрации
        updated_at: Дата последнего обновления
    """
    
    __tablename__ = "users"
    
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
    
    # Отношения
    games = relationship("Game", back_populates="user", lazy="dynamic")
    duels = relationship("Duel", foreign_keys="Duel.player1_id", lazy="dynamic")


class Question(Base):
    """Модель вопроса.
    
    Attributes:
        id: Уникальный ID вопроса
        text: Текст вопроса
        category: Категория
        difficulty: Уровень сложности
        correct_answer: Правильный ответ
        wrong_answers: Неправильные ответы (JSON массив)
        explanation: Объяснение ответа
        source: Источник вопроса (RuBQ, OpenTDB, etc.)
        source_id: ID в источнике
        is_active: Активен ли вопрос
        usage_count: Сколько раз использовался
        correct_rate: Процент правильных ответов
        created_at: Дата добавления
    """
    
    __tablename__ = "questions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    category = Column(Enum(QuestionCategory), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    
    # Ответы
    correct_answer = Column(Text, nullable=False)
    wrong_answers = Column(JSON, nullable=False)  # Массив из 3 неправильных ответов
    explanation = Column(Text, nullable=True)
    
    # Метаданные источника
    source = Column(String(50), nullable=False)  # rubq, opentdb, custom
    source_id = Column(String(100), nullable=True)
    
    # Статистика использования
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    correct_rate = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=func.now())
    
    # Отношения
    game_questions = relationship("GameQuestion", back_populates="question", lazy="dynamic")


class Game(Base):
    """Модель игровой сессии.
    
    Attributes:
        id: Уникальный ID игры
        user_id: ID пользователя
        category: Выбранная категория
        difficulty: Выбранная сложность
        question_count: Количество вопросов
        status: Статус игры
        score: Набранные очки
        correct_answers: Количество правильных ответов
        lives_remaining: Оставшиеся жизни
        started_at: Время начала
        completed_at: Время завершения
    """
    
    __tablename__ = "games"
    
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
    
    # Отношения
    user = relationship("User", back_populates="games")
    questions = relationship("GameQuestion", back_populates="game", lazy="dynamic")


class GameQuestion(Base):
    """Связующая модель между игрой и вопросами.
    
    Attributes:
        id: Уникальный ID записи
        game_id: ID игры
        question_id: ID вопроса
        was_answered: Был ли дан ответ
        is_correct: Правильный ли ответ
        answer_time: Время ответа в секундах
        points_earned: Полученные очки
        answered_at: Время ответа
    """
    
    __tablename__ = "game_questions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(BigInteger, ForeignKey("games.id"), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id"), nullable=False)
    
    # Ответ пользователя
    was_answered = Column(Boolean, default=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answer_time = Column(Float, nullable=True)  # Время в секундах
    points_earned = Column(Integer, default=0)
    
    answered_at = Column(DateTime, nullable=True)
    
    # Отношения
    game = relationship("Game", back_populates="questions")
    question = relationship("Question", back_populates="game_questions")


class Duel(Base):
    """Модель дуэли между двумя игроками.
    
    Attributes:
        id: Уникальный ID дуэли
        player1_id: ID первого игрока
        player2_id: ID второго игрока (null если ожидание)
        category: Категория вопросов
        question_count: Количество вопросов
        status: Статус дуэли
        player1_score: Счёт первого игрока
        player2_score: Счёт второго игрока
        winner_id: ID победителя
        created_at: Время создания
        started_at: Время начала
        completed_at: Время завершения
    """
    
    __tablename__ = "duels"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player1_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    player2_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    # Настройки дуэли
    category = Column(Enum(QuestionCategory), nullable=False)
    question_count = Column(Integer, default=5)
    status = Column(Enum(DuelStatus), default=DuelStatus.WAITING)
    
    # Счёт
    player1_score = Column(Integer, default=0)
    player2_score = Column(Integer, default=0)
    player1_correct = Column(Integer, default=0)
    player2_correct = Column(Integer, default=0)
    
    # Результат
    winner_id = Column(BigInteger, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Отношения
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])


class Payment(Base):
    """Модель платежа за Premium.
    
    Attributes:
        id: Уникальный ID платежа
        user_id: ID пользователя
        amount: Сумма платежа
        currency: Валюта
        provider: Платёжная система
        status: Статус платежа
        subscription_until: Дата окончания подписки
        created_at: Время создания
        completed_at: Время завершения
    """
    
    __tablename__ = "payments"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Детали платежа
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    provider = Column(String(50), default="yookassa")  # yookassa, stripe
    provider_payment_id = Column(String(255), nullable=True)
    
    # Статус
    status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    
    # Подписка
    subscription_until = Column(DateTime, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)


class AnalyticsEvent(Base):
    """Модель для аналитических событий.
    
    Attributes:
        id: Уникальный ID события
        user_id: ID пользователя (может быть null)
        event_type: Тип события
        event_data: Данные события (JSON)
        created_at: Время события
    """
    
    __tablename__ = "analytics_events"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=func.now())


class DailyStreak(Base):
    """Модель для отслеживания daily streaks.
    
    Attributes:
        id: Уникальный ID записи
        user_id: ID пользователя
        streak_date: Дата streak
        streak_count: Текущий счётчик streak
        reward_claimed: Получена ли награда
    """
    
    __tablename__ = "daily_streaks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    streak_date = Column(DateTime, nullable=False)
    streak_count = Column(Integer, default=1)
    reward_claimed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
