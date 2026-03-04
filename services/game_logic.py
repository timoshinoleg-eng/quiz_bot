"""Игровая логика для MAX-Квиз.

Этот модуль содержит бизнес-логику игры:
- Расчёт очков
- Управление жизнями
- Таймеры
- Подсказки

Example:
    >>> from services.game_logic import GameSession
    >>> session = GameSession(game_id, user_id)
    >>> await session.start()
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from config import settings
from db import get_db, db_manager
from models import Game, GameQuestion, Question, GameStatus


logger = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    """Результат ответа на вопрос.
    
    Attributes:
        is_correct: Правильный ли ответ
        points_earned: Полученные очки
        time_bonus: Бонус за скорость
        lives_remaining: Оставшиеся жизни
        game_over: Игра окончена
        correct_answer: Правильный ответ (если ошибка)
    """
    is_correct: bool
    points_earned: int
    time_bonus: int
    lives_remaining: int
    game_over: bool
    correct_answer: Optional[str] = None


@dataclass
class GameStats:
    """Статистика игры.
    
    Attributes:
        total_questions: Всего вопросов
        answered_questions: Отвечено вопросов
        correct_answers: Правильных ответов
        total_score: Общий счёт
        lives_remaining: Оставшиеся жизни
        average_time: Среднее время ответа
        accuracy: Точность (%)
    """
    total_questions: int
    answered_questions: int
    correct_answers: int
    total_score: int
    lives_remaining: int
    average_time: float
    accuracy: float


class GameSession:
    """Сессия игры.
    
    Управляет состоянием игры, таймерами и подсказками.
    """
    
    def __init__(self, game_id: int, user_id: int):
        """Инициализирует игровую сессию.
        
        Args:
            game_id: ID игры
            user_id: ID пользователя
        """
        self.game_id = game_id
        self.user_id = user_id
        self.game: Optional[Game] = None
        self.questions: List[Question] = []
        self.current_question_index: int = 0
        self.question_start_time: Optional[datetime] = None
        self._timer_task: Optional[asyncio.Task] = None
        self._hints_used: Dict[str, bool] = field(default_factory=dict)
    
    async def start(self) -> None:
        """Запускает игровую сессию."""
        self.game = await db_manager.get_game(self.game_id)
        
        if not self.game:
            raise ValueError(f"Game {self.game_id} not found")
        
        # Загружаем вопросы
        from sqlalchemy import select
        async with get_db() as db:
            result = await db.execute(
                select(Question)
                .join(GameQuestion)
                .where(GameQuestion.game_id == self.game_id)
                .order_by(GameQuestion.id)
            )
            self.questions = result.scalars().all()
        
        self.current_question_index = 0
        self._start_question_timer()
        
        logger.info(f"Game session {self.game_id} started for user {self.user_id}")
    
    def _start_question_timer(self) -> None:
        """Запускает таймер для текущего вопроса."""
        self.question_start_time = datetime.utcnow()
        
        # Отменяем предыдущий таймер если есть
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        # Создаём новый таймер
        self._timer_task = asyncio.create_task(
            self._question_timeout()
        )
    
    async def _question_timeout(self) -> None:
        """Обрабатывает таймаут вопроса."""
        try:
            await asyncio.sleep(settings.GAME.answer_timeout)
            
            # Время вышло - считаем неправильным ответом
            logger.info(f"Question timeout for game {self.game_id}")
            await self.submit_answer(None, timed_out=True)
            
        except asyncio.CancelledError:
            # Таймер отменён (ответ дан вовремя)
            pass
    
    async def submit_answer(
        self,
        answer: Optional[str],
        timed_out: bool = False
    ) -> AnswerResult:
        """Обрабатывает ответ пользователя.
        
        Args:
            answer: Ответ пользователя
            timed_out: Время вышло
            
        Returns:
            AnswerResult: Результат ответа
        """
        if not self.game or not self.questions:
            raise ValueError("Game session not started")
        
        # Отменяем таймер
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        current_question = self.questions[self.current_question_index]
        
        # Вычисляем время ответа
        answer_time = 0.0
        if self.question_start_time:
            answer_time = (datetime.utcnow() - self.question_start_time).total_seconds()
        
        # Проверяем ответ
        is_correct = False
        if answer and not timed_out:
            is_correct = answer.lower().strip() == current_question.correct_answer.lower().strip()
        
        # Вычисляем очки
        points, time_bonus = self._calculate_points(is_correct, answer_time)
        
        # Обновляем жизни
        if not is_correct:
            self.game.lives_remaining -= 1
        
        # Сохраняем результат
        await self._save_answer_result(
            current_question.id,
            answer,
            is_correct,
            answer_time,
            points + time_bonus
        )
        
        # Проверяем конец игры
        game_over = (
            self.game.lives_remaining <= 0 or
            self.current_question_index >= len(self.questions) - 1
        )
        
        if game_over:
            await self._finish_game()
        else:
            self.current_question_index += 1
            self._start_question_timer()
        
        return AnswerResult(
            is_correct=is_correct,
            points_earned=points,
            time_bonus=time_bonus,
            lives_remaining=self.game.lives_remaining,
            game_over=game_over,
            correct_answer=current_question.correct_answer if not is_correct else None
        )
    
    def _calculate_points(self, is_correct: bool, answer_time: float) -> tuple:
        """Вычисляет очки за ответ.
        
        Args:
            is_correct: Правильный ли ответ
            answer_time: Время ответа в секундах
            
        Returns:
            tuple: (базовые очки, бонус за скорость)
        """
        if not is_correct:
            return 0, 0
        
        base_points = settings.GAME.points_correct
        
        # Бонус за скорость: чем быстрее, тем больше бонус
        max_time = settings.GAME.answer_timeout
        if answer_time < max_time:
            # Линейный бонус: максимум при ответе за 0 секунд
            speed_ratio = 1 - (answer_time / max_time)
            time_bonus = int(settings.GAME.points_speed_bonus * speed_ratio)
        else:
            time_bonus = 0
        
        return base_points, time_bonus
    
    async def _save_answer_result(
        self,
        question_id: int,
        answer: Optional[str],
        is_correct: bool,
        answer_time: float,
        points: int
    ) -> None:
        """Сохраняет результат ответа в БД.
        
        Args:
            question_id: ID вопроса
            answer: Ответ пользователя
            is_correct: Правильный ли ответ
            answer_time: Время ответа
            points: Полученные очки
        """
        async with get_db() as db:
            game_question = GameQuestion(
                game_id=self.game_id,
                question_id=question_id,
                was_answered=True,
                user_answer=answer,
                is_correct=is_correct,
                answer_time=answer_time,
                points_earned=points,
                answered_at=datetime.utcnow()
            )
            db.add(game_question)
            
            # Обновляем счёт игры
            self.game.score += points
            if is_correct:
                self.game.correct_answers += 1
    
    async def _finish_game(self) -> None:
        """Завершает игру."""
        self.game.status = GameStatus.COMPLETED
        self.game.completed_at = datetime.utcnow()
        
        # Обновляем статистику пользователя
        user = await db_manager.get_or_create_user(self.user_id)
        user.score_total += self.game.score
        user.games_played += 1
        
        # Проверяем победу (все вопросы правильно)
        if self.game.correct_answers == self.game.question_count:
            user.games_won += 1
        
        logger.info(f"Game {self.game_id} finished. Score: {self.game.score}")
    
    async def use_hint(self, hint_type: str) -> Dict[str, Any]:
        """Использует подсказку.
        
        Args:
            hint_type: Тип подсказки (50_50, time, skip)
            
        Returns:
            Dict: Результат использования подсказки
        """
        if hint_type in self._hints_used:
            return {"success": False, "error": "Hint already used"}
        
        self._hints_used[hint_type] = True
        
        current_question = self.questions[self.current_question_index]
        
        if hint_type == "50_50":
            # Убираем 2 неправильных ответа
            wrong_answers = current_question.wrong_answers[:2]
            return {
                "success": True,
                "hint_type": "50_50",
                "removed_answers": wrong_answers
            }
        
        elif hint_type == "time":
            # Добавляем 15 секунд
            # В реальности нужно обновить таймер
            return {
                "success": True,
                "hint_type": "time",
                "extra_time": 15
            }
        
        elif hint_type == "skip":
            # Пропускаем вопрос, считаем правильным
            await self.submit_answer(current_question.correct_answer)
            return {
                "success": True,
                "hint_type": "skip",
                "message": "Question skipped"
            }
        
        return {"success": False, "error": "Unknown hint type"}
    
    def get_current_question(self) -> Optional[Question]:
        """Получает текущий вопрос.
        
        Returns:
            Optional[Question]: Текущий вопрос или None
        """
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    def get_remaining_time(self) -> int:
        """Получает оставшееся время на текущий вопрос.
        
        Returns:
            int: Оставшиеся секунды
        """
        if not self.question_start_time:
            return settings.GAME.answer_timeout
        
        elapsed = (datetime.utcnow() - self.question_start_time).total_seconds()
        remaining = settings.GAME.answer_timeout - int(elapsed)
        
        return max(0, remaining)
    
    async def get_stats(self) -> GameStats:
        """Получает статистику текущей игры.
        
        Returns:
            GameStats: Статистика игры
        """
        if not self.game:
            raise ValueError("Game session not started")
        
        # Вычисляем среднее время
        async with get_db() as db:
            from sqlalchemy import func
            from models import GameQuestion
            
            result = await db.execute(
                select(func.avg(GameQuestion.answer_time))
                .where(GameQuestion.game_id == self.game_id)
            )
            avg_time = result.scalar() or 0.0
        
        accuracy = 0.0
        if self.current_question_index > 0:
            accuracy = (self.game.correct_answers / self.current_question_index) * 100
        
        return GameStats(
            total_questions=self.game.question_count,
            answered_questions=self.current_question_index,
            correct_answers=self.game.correct_answers,
            total_score=self.game.score,
            lives_remaining=self.game.lives_remaining,
            average_time=avg_time,
            accuracy=accuracy
        )


class StreakManager:
    """Менеджер для daily streaks."""
    
    STREAK_REWARDS = {
        1: 10,
        2: 20,
        3: 30,
        5: 50,
        7: 100,
        14: 200,
        30: 500,
    }
    
    @classmethod
    async def check_streak(cls, user_id: int) -> Dict[str, Any]:
        """Проверяет и обновляет streak пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict: Информация о streak
        """
        user = await db_manager.get_or_create_user(user_id)
        
        today = datetime.utcnow().date()
        last_played = user.last_played.date() if user.last_played else None
        
        if last_played is None:
            # Первый вход
            user.daily_streak = 1
            reward = cls.STREAK_REWARDS.get(1, 10)
            
        elif last_played == today:
            # Уже играл сегодня
            reward = 0
            
        elif (today - last_played).days == 1:
            # Продолжаем streak
            user.daily_streak += 1
            reward = cls.STREAK_REWARDS.get(user.daily_streak, 50)
            
        else:
            # Streak прерван
            user.daily_streak = 1
            reward = cls.STREAK_REWARDS.get(1, 10)
        
        user.last_played = datetime.utcnow()
        
        return {
            "streak": user.daily_streak,
            "reward": reward,
            "continued": last_played is not None and (today - last_played).days == 1
        }
    
    @classmethod
    def get_next_milestone(cls, current_streak: int) -> Optional[int]:
        """Получает следующий milestone для streak.
        
        Args:
            current_streak: Текущий streak
            
        Returns:
            Optional[int]: Следующий milestone или None
        """
        milestones = sorted(cls.STREAK_REWARDS.keys())
        
        for milestone in milestones:
            if milestone > current_streak:
                return milestone
        
        return None


class LeaderboardService:
    """Сервис для работы с таблицей лидеров."""
    
    @staticmethod
    async def get_top_players(
        period: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Получает топ игроков.
        
        Args:
            period: Период (day, week, month, all)
            limit: Количество игроков
            
        Returns:
            List[Dict]: Список топ игроков
        """
        from sqlalchemy import select, func
        from models import User, Game
        
        async with get_db() as db:
            query = select(User).order_by(User.score_total.desc()).limit(limit)
            
            if period == "day":
                from datetime import timedelta
                since = datetime.utcnow() - timedelta(days=1)
                # Добавить фильтрацию по дате
            elif period == "week":
                from datetime import timedelta
                since = datetime.utcnow() - timedelta(weeks=1)
            elif period == "month":
                from datetime import timedelta
                since = datetime.utcnow() - timedelta(days=30)
            
            result = await db.execute(query)
            users = result.scalars().all()
            
            return [
                {
                    "rank": i + 1,
                    "user_id": u.id,
                    "username": u.username,
                    "score": u.score_total,
                    "games": u.games_played,
                }
                for i, u in enumerate(users)
            ]
    
    @staticmethod
    async def get_user_rank(user_id: int) -> Optional[int]:
        """Получает ранг пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[int]: Ранг или None
        """
        from sqlalchemy import select, func
        from models import User
        
        async with get_db() as db:
            # Получаем счёт пользователя
            result = await db.execute(
                select(User.score_total).where(User.id == user_id)
            )
            user_score = result.scalar()
            
            if user_score is None:
                return None
            
            # Считаем сколько игроков с большим счётом
            result = await db.execute(
                select(func.count(User.id)).where(User.score_total > user_score)
            )
            higher_count = result.scalar()
            
            return higher_count + 1


# Глобальные сессии игр (в продакшене использовать Redis)
active_sessions: Dict[int, GameSession] = {}


async def get_game_session(game_id: int, user_id: int) -> GameSession:
    """Получает или создаёт игровую сессию.
    
    Args:
        game_id: ID игры
        user_id: ID пользователя
        
    Returns:
        GameSession: Игровая сессия
    """
    session_key = f"{user_id}:{game_id}"
    
    if session_key not in active_sessions:
        session = GameSession(game_id, user_id)
        await session.start()
        active_sessions[session_key] = session
    
    return active_sessions[session_key]


async def remove_game_session(game_id: int, user_id: int) -> None:
    """Удаляет игровую сессию.
    
    Args:
        game_id: ID игры
        user_id: ID пользователя
    """
    session_key = f"{user_id}:{game_id}"
    
    if session_key in active_sessions:
        del active_sessions[session_key]
