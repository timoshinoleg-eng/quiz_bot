"""Small domain facade kept for integrations that used the old game module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings
from db import db_manager, get_db
from models import GameStatus, User


@dataclass
class AnswerResult:
    is_correct: bool
    points_earned: int
    time_bonus: int
    lives_remaining: int
    game_over: bool
    correct_answer: Optional[str] = None
    duplicate: bool = False


@dataclass
class GameStats:
    total_questions: int
    answered_questions: int
    correct_answers: int
    total_score: int
    lives_remaining: int
    average_time: float
    accuracy: float


class GameSession:
    """Persistent game session; no gameplay state is kept only in memory."""

    def __init__(self, game_id: int, user_id: int):
        self.game_id = game_id
        self.user_id = user_id
        self.game = None
        self.questions = []

    async def start(self) -> None:
        self.game = await db_manager.get_game(self.game_id)
        if not self.game or self.game.user_id != self.user_id:
            raise ValueError(f"Game {self.game_id} not found")
        self.questions = await db_manager.get_game_questions(self.game_id)

    def _calculate_points(self, is_correct: bool, answer_time: float) -> tuple[int, int]:
        if not is_correct:
            return 0, 0
        timeout = max(1, settings.GAME.answer_timeout)
        bonus = int(settings.GAME.points_speed_bonus * max(0.0, 1.0 - min(answer_time, timeout) / timeout))
        return settings.GAME.points_correct, bonus

    async def submit_index(self, position: int, selected_index: int) -> AnswerResult:
        result = await db_manager.answer_game(self.game_id, self.user_id, position, selected_index, settings.GAME.answer_timeout)
        if not result.get("ok"):
            raise ValueError(result.get("error", "answer_failed"))
        game = result["game"]
        return AnswerResult(
            is_correct=result.get("correct", False),
            points_earned=result.get("points", 0),
            time_bonus=max(0, result.get("points", 0) - settings.GAME.points_correct),
            lives_remaining=game.lives_remaining,
            game_over=result.get("game_over", False),
            correct_answer=result.get("correct_answer"),
            duplicate=result.get("duplicate", False),
        )

    async def submit_answer(self, answer: Optional[str], timed_out: bool = False) -> AnswerResult:
        if not self.game:
            await self.start()
        question = await db_manager.get_current_question(self.game_id)
        if not question:
            raise ValueError("No current question")
        selected_index = -1
        if answer is not None and not timed_out:
            selected_index = next((index for index, option in enumerate(question.answer_options)
                                   if option.strip().lower() == answer.strip().lower()), -1)
        return await self.submit_index(question.position, selected_index)


class StreakManager:
    @staticmethod
    async def check_streak(user_id: int) -> Dict[str, Any]:
        async with get_db() as session:
            user = await session.get(User, user_id)
            if user is None:
                user = User(id=user_id)
                session.add(user)
                await session.flush()
            previous = user.daily_streak or 0
            today = datetime.utcnow().date()
            if user.last_daily_date == today:
                continued = previous > 1
            elif user.last_daily_date == today - timedelta(days=1):
                user.daily_streak = previous + 1
                user.best_streak = max(user.best_streak or 0, user.daily_streak)
                continued = True
            else:
                user.daily_streak = 1
                user.best_streak = max(user.best_streak or 0, 1)
                continued = False
            user.last_daily_date = today
            return {"streak": user.daily_streak, "reward": 10, "continued": continued}

    @staticmethod
    def get_next_milestone(streak: int) -> Optional[int]:
        milestones = [2, 3, 5, 7, 14, 30]
        return next((milestone for milestone in milestones if milestone > streak), None)


class LeaderboardService:
    @staticmethod
    async def get_top_players(limit: int = 10) -> List[Dict[str, Any]]:
        return await db_manager.get_weekly_leaderboard(limit)


async def get_game_stats(game_id: int) -> Optional[GameStats]:
    game = await db_manager.get_game(game_id)
    if not game:
        return None
    questions = await db_manager.get_game_questions(game_id)
    times = [question.answer_time for question in questions if question.answer_time is not None]
    answered = game.answered_questions
    return GameStats(
        total_questions=game.question_count,
        answered_questions=answered,
        correct_answers=game.correct_answers,
        total_score=game.score,
        lives_remaining=game.lives_remaining,
        average_time=sum(times) / len(times) if times else 0.0,
        accuracy=(game.correct_answers / answered * 100) if answered else 0.0,
    )
