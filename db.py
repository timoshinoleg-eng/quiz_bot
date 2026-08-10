"""Async persistence and server-authoritative game operations."""

from __future__ import annotations

import logging
import random
import secrets
import string
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from config import settings
from models import (
    AnalyticsEvent,
    ChallengeAttempt,
    ChallengeQuestion,
    ChallengeStatus,
    DailyChallenge,
    DailyQuestion,
    DailyResult,
    DifficultyLevel,
    FriendChallenge,
    Game,
    GameMode,
    GameQuestion,
    GameStatus,
    Question,
    QuestionCategory,
    QuizPack,
    QuizPackQuestion,
    User,
    PlatformIdentity,
    UserQuestionHistory,
)

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def utcnow() -> datetime:
    return datetime.utcnow()


def utcdate() -> date:
    return utcnow().date()


def value_of(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def get_database_url() -> str:
    return settings.DATABASE.url or "sqlite+aiosqlite:///./quiz_bot.db"


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_database_url()
        kwargs: Dict[str, Any] = {
            "echo": settings.DEBUG,
            "pool_pre_ping": True,
        }
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs.update(pool_size=settings.DATABASE.pool_size, max_overflow=settings.DATABASE.max_overflow)
        _engine = create_async_engine(url, **kwargs)
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)
    return _session_factory


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = get_session_maker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    from models import Base

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def _normalise_options(question: Question) -> tuple[list[str], int]:
    options = [str(question.correct_answer), *[str(answer) for answer in (question.wrong_answers or [])]]
    options = list(dict.fromkeys(answer.strip() for answer in options if answer.strip()))
    if len(options) < 2 or question.correct_answer.strip() not in options:
        raise ValueError(f"Question {question.id} has invalid answer options")
    random.shuffle(options)
    return options, options.index(question.correct_answer.strip())


class DailyAlreadyPlayed(Exception):
    """Raised with a stable identifier when a completed Daily is reopened."""

    def __init__(self, game_id: int):
        self.game_id = game_id
        super().__init__("Daily challenge already completed")


class ChallengeError(Exception):
    pass


class DatabaseManager:
    """All state-changing methods are idempotent at the callback boundary."""

    async def get_or_create_user(self, user_id: int, username: Optional[str] = None,
                                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        async with get_db() as db:
            user = await db.get(User, user_id)
            if user is None:
                user = User(id=user_id, username=username, first_name=first_name, last_name=last_name)
                db.add(user)
                await db.flush()
            else:
                if username is not None:
                    user.username = username
                if first_name is not None:
                    user.first_name = first_name
                if last_name is not None:
                    user.last_name = last_name
            return user

    async def get_or_create_platform_user(self, platform: str, external_user_id: int | str,
                                          username: Optional[str] = None, first_name: Optional[str] = None,
                                          last_name: Optional[str] = None) -> User:
        """Resolve a platform identity without conflating MAX and Telegram numeric IDs."""
        if platform not in {"max", "telegram"}:
            raise ValueError("unsupported platform")
        external = str(external_user_id)
        async with get_db() as db:
            identity = await db.scalar(select(PlatformIdentity).where(
                PlatformIdentity.platform == platform, PlatformIdentity.external_user_id == external))
            if identity:
                user = await db.get(User, identity.user_id)
                identity.username, identity.first_name, identity.last_name = username, first_name, last_name
                if user:
                    user.username = username or user.username
                    user.first_name = first_name or user.first_name
                    user.last_name = last_name or user.last_name
                    return user
            # Old MAX rows used the external ID as their user ID. Preserve that compatibility;
            # Telegram IDs are mapped to a deterministic negative core ID to avoid collisions.
            core_id = int(external) if platform == "max" else -(int(external) + 1)
            user = await db.get(User, core_id)
            if user is None:
                user = User(id=core_id, username=username, first_name=first_name, last_name=last_name)
                db.add(user)
                await db.flush()
            db.add(PlatformIdentity(user_id=user.id, platform=platform, external_user_id=external,
                                    username=username, first_name=first_name, last_name=last_name))
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        async with get_db() as db:
            return await db.get(User, user_id)

    async def is_premium(self, user_id: int) -> bool:
        return False

    async def log_event(self, event_type: str, user_id: Optional[int] = None,
                        event_data: Optional[Dict[str, Any]] = None) -> None:
        async with get_db() as db:
            db.add(AnalyticsEvent(user_id=user_id, event_type=event_type, event_data=event_data or {}))

    async def update_user_state(self, user_id: int, state: Optional[str], data: Optional[Dict[str, Any]] = None) -> None:
        async with get_db() as db:
            user = await db.get(User, user_id)
            if user:
                user.current_state = state
                user.state_data = data or {}

    async def get_user_state(self, user_id: int) -> tuple[Optional[str], Dict[str, Any]]:
        async with get_db() as db:
            user = await db.get(User, user_id)
            return (user.current_state, user.state_data or {}) if user else (None, {})

    async def _question_pool(self, db: AsyncSession, category: Any, difficulty: Any,
                             count: int, user_id: Optional[int] = None,
                             pack_slug: Optional[str] = None) -> List[Question]:
        category_value = value_of(category)
        difficulty_value = value_of(difficulty)
        query = (
            select(Question, UserQuestionHistory)
            .outerjoin(UserQuestionHistory, (UserQuestionHistory.question_id == Question.id) &
                       (UserQuestionHistory.user_id == user_id if user_id is not None else False))
            .where(Question.is_active.is_(True))
        )
        if pack_slug:
            query = query.join(QuizPackQuestion, QuizPackQuestion.question_id == Question.id).join(
                QuizPack, QuizPack.id == QuizPackQuestion.quiz_pack_id
            ).where(QuizPack.slug == pack_slug, QuizPack.active.is_(True))
        else:
            query = query.where(Question.category == category_value)
        query = query.where(Question.difficulty == difficulty_value)
        rows = list((await db.execute(query)).all())
        # ``general`` is the cross-pack Quick/Daily mode.  The V2 corpus is
        # intentionally organised into concrete packs, not a catch-all bucket.
        if not rows and not pack_slug and category_value == QuestionCategory.GENERAL.value:
            broad_query = (
                select(Question, UserQuestionHistory)
                .outerjoin(UserQuestionHistory, (UserQuestionHistory.question_id == Question.id) &
                           (UserQuestionHistory.user_id == user_id if user_id is not None else False))
                .where(Question.is_active.is_(True), Question.difficulty == difficulty_value)
            )
            rows = list((await db.execute(broad_query)).all())
        # A transparent unseen-first policy.  Earlier mistakes are then repeated before
        # already-mastered material; least recently seen breaks ties.
        random.shuffle(rows)
        rows.sort(key=lambda row: (
            0 if row[1] is None else 1,
            0 if row[1] is not None and not row[1].last_is_correct else 1,
            row[1].last_seen_at if row[1] and row[1].last_seen_at else datetime.min,
        ))
        questions = [row[0] for row in rows[:count]]
        if len(questions) < count:
            fallback = (
                select(Question)
                .where(Question.is_active.is_(True))
                .where(Question.difficulty == difficulty_value)
                .where(Question.id.not_in([q.id for q in questions] or [-1]))
                .order_by(func.random())
                .limit(count - len(questions))
            )
            questions.extend((await db.execute(fallback)).scalars().all())
        if len(questions) < count:
            raise ValueError(f"Not enough questions for {category_value}/{difficulty_value}: {len(questions)} < {count}")
        return questions

    async def available_question_count(self, category: Any, difficulty: Any) -> int:
        """Return the number of questions selectable by the current pool policy."""
        category_value = value_of(category)
        difficulty_value = value_of(difficulty)
        async with get_db() as db:
            exact_count = await db.scalar(
                select(func.count(Question.id))
                .where(Question.is_active.is_(True))
                .where(Question.category == category_value)
                .where(Question.difficulty == difficulty_value)
            )
            if category_value == QuestionCategory.GENERAL.value:
                return int(exact_count or 0)
            fallback_count = await db.scalar(
                select(func.count(Question.id))
                .where(Question.is_active.is_(True))
                .where(Question.category == QuestionCategory.GENERAL.value)
            )
            return int(exact_count or 0) + int(fallback_count or 0)

    async def _new_game(self, db: AsyncSession, user_id: int, category: Any, difficulty: Any,
                        question_count: int, mode: Any = GameMode.SOLO, daily_date: Optional[date] = None,
                        challenge_id: Optional[int] = None, question_ids: Optional[Sequence[int]] = None,
                        pack_slug: Optional[str] = None) -> Game:
        if question_count not in (5, 7, 10, 15, 20):
            raise ValueError("question_count must be one of 5, 7, 10, 15, 20")
        if question_ids is None:
            questions = await self._question_pool(db, category, difficulty, question_count, user_id, pack_slug)
        else:
            rows = (await db.execute(select(Question).where(Question.id.in_(list(question_ids))))).scalars().all()
            by_id = {row.id: row for row in rows}
            try:
                questions = [by_id[int(question_id)] for question_id in question_ids]
            except KeyError as exc:
                raise ValueError("Immutable question set contains a missing question") from exc
            if len(questions) != question_count:
                raise ValueError("Immutable question set has the wrong size")

        game = Game(
            user_id=user_id,
            mode=value_of(mode),
            category=value_of(category),
            difficulty=value_of(difficulty),
            question_count=question_count,
            daily_date=daily_date,
            challenge_id=challenge_id,
        )
        db.add(game)
        await db.flush()
        for position, question in enumerate(questions):
            options, correct_index = _normalise_options(question)
            db.add(GameQuestion(
                game_id=game.id,
                question_id=question.id,
                position=position,
                answer_options=options,
                correct_index=correct_index,
                sent_at=utcnow() if position == 0 else None,
            ))
        await db.flush()
        return game

    async def create_game(self, user_id: int, category: Any = QuestionCategory.GENERAL,
                          difficulty: Any = DifficultyLevel.MEDIUM, question_count: int = 5,
                          mode: Any = GameMode.SOLO, daily_date: Optional[date] = None,
                        challenge_id: Optional[int] = None, question_ids: Optional[Sequence[int]] = None,
                        pack_slug: Optional[str] = None) -> Game:
        async with get_db() as db:
            return await self._new_game(db, user_id, category, difficulty, question_count, mode, daily_date,
                                        challenge_id, question_ids, pack_slug)

    async def get_game(self, game_id: int) -> Optional[Game]:
        async with get_db() as db:
            return await db.get(Game, game_id)

    async def get_game_questions(self, game_id: int) -> List[GameQuestion]:
        async with get_db() as db:
            result = await db.execute(select(GameQuestion).options(selectinload(GameQuestion.question)).where(GameQuestion.game_id == game_id).order_by(GameQuestion.position))
            return list(result.scalars().all())

    async def get_current_question(self, game_id: int) -> Optional[GameQuestion]:
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if not game:
                return None
            result = await db.execute(select(GameQuestion).options(selectinload(GameQuestion.question)).where(
                GameQuestion.game_id == game_id,
                GameQuestion.position == game.current_question_index,
            ))
            question = result.scalar_one_or_none()
            if question and question.sent_at is None:
                question.sent_at = utcnow()
            return question

    async def answer_game(self, game_id: int, user_id: int, position: int, selected_index: int,
                          answer_timeout: int = 30) -> Dict[str, Any]:
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if not game or game.user_id != user_id:
                return {"ok": False, "error": "game_not_found"}
            question_result = await db.execute(select(GameQuestion).options(selectinload(GameQuestion.question)).where(
                GameQuestion.game_id == game_id,
                GameQuestion.position == position,
            ))
            game_question = question_result.scalar_one_or_none()
            if not game_question:
                return {"ok": False, "error": "question_not_found"}
            if game_question.was_answered:
                return {"ok": True, "duplicate": True, "game": game}
            if game.status != GameStatus.IN_PROGRESS.value or position != game.current_question_index:
                return {"ok": False, "error": "stale_question"}
            if selected_index < -1 or selected_index >= len(game_question.answer_options):
                return {"ok": False, "error": "invalid_answer"}

            now = utcnow()
            elapsed = max(0.0, (now - (game_question.sent_at or now)).total_seconds())
            correct = selected_index >= 0 and selected_index == game_question.correct_index
            points = 0
            if correct:
                speed_ratio = max(0.0, 1.0 - min(elapsed, float(answer_timeout)) / answer_timeout)
                points = 100 + int(50 * speed_ratio)

            game_question.was_answered = True
            game_question.selected_index = selected_index
            game_question.is_correct = correct
            game_question.answer_time = elapsed
            game_question.points_earned = points
            game_question.answered_at = now
            history = await db.scalar(select(UserQuestionHistory).where(
                UserQuestionHistory.user_id == user_id,
                UserQuestionHistory.question_id == game_question.question_id,
            ))
            if history is None:
                history = UserQuestionHistory(user_id=user_id, question_id=game_question.question_id)
                db.add(history)
            history.times_seen = int(history.times_seen or 0) + 1
            history.times_correct = int(history.times_correct or 0) + int(correct)
            history.last_seen_at = now
            history.last_is_correct = correct
            game.score += points
            game.correct_answers += int(correct)
            game.answered_questions += 1
            if not correct:
                game.lives_remaining -= 1
            game.current_question_index = position + 1

            finished = game.lives_remaining <= 0 or game.current_question_index >= game.question_count
            if finished:
                game.status = GameStatus.COMPLETED
                game.finished_reason = "lives" if game.lives_remaining <= 0 else "complete"
                game.completed_at = now
                await self._award_progress(db, game)
            else:
                next_question = await db.execute(select(GameQuestion).where(
                    GameQuestion.game_id == game_id,
                    GameQuestion.position == game.current_question_index,
                ))
                next_row = next_question.scalar_one_or_none()
                if next_row and next_row.sent_at is None:
                    next_row.sent_at = now

            return {
                "ok": True,
                "duplicate": False,
                "correct": correct,
                "points": points,
                "correct_answer": game_question.question.correct_answer if not correct else None,
                "game_over": finished,
                "game": game,
                "question": game_question,
            }

    async def _award_progress(self, db: AsyncSession, game: Game) -> None:
        if game.progress_awarded:
            return
        user = await db.get(User, game.user_id)
        if not user:
            return
        user.score_total += game.score
        user.games_played += 1
        if game.correct_answers == game.question_count:
            user.games_won += 1
        user.xp += 45 + game.correct_answers * 10
        user.level = max(1, user.xp // 500 + 1)
        achievements = list(user.achievements or [])
        if "first_game" not in achievements:
            achievements.append("first_game")
        if game.correct_answers == game.question_count and "perfect" not in achievements:
            achievements.append("perfect")

        if game.mode == GameMode.DAILY.value and game.daily_date:
            daily = await db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == game.daily_date))
            if daily:
                existing = await db.scalar(select(DailyResult).where(
                    DailyResult.daily_id == daily.id,
                    DailyResult.user_id == game.user_id,
                ))
                if existing is None:
                    db.add(DailyResult(daily_id=daily.id, user_id=game.user_id, game_id=game.id,
                                       score=game.score, correct_answers=game.correct_answers, completed_at=utcnow()))
                    if user.last_daily_date == game.daily_date - timedelta(days=1):
                        user.daily_streak += 1
                    elif user.last_daily_date != game.daily_date:
                        user.daily_streak = 1
                    user.last_daily_date = game.daily_date
                    user.best_streak = max(user.best_streak, user.daily_streak)
                    if user.daily_streak >= 3 and "streak_3" not in achievements:
                        achievements.append("streak_3")
                    if user.daily_streak >= 7 and "streak_7" not in achievements:
                        achievements.append("streak_7")

        if game.challenge_id:
            attempt = await db.scalar(select(ChallengeAttempt).where(
                ChallengeAttempt.challenge_id == game.challenge_id,
                ChallengeAttempt.user_id == game.user_id,
            ))
            if attempt:
                attempt.score = game.score
                attempt.correct_answers = game.correct_answers
                attempt.completed_at = game.completed_at or utcnow()
            challenge = await db.get(FriendChallenge, game.challenge_id)
            if challenge:
                await db.flush()
                completed = await db.scalar(select(func.count(ChallengeAttempt.id)).where(
                    ChallengeAttempt.challenge_id == challenge.id,
                    ChallengeAttempt.completed_at.is_not(None),
                ))
                if completed >= 2:
                    challenge.status = ChallengeStatus.COMPLETED.value
                    challenge.completed_at = game.completed_at or utcnow()
                else:
                    challenge.status = ChallengeStatus.IN_PROGRESS.value
        user.achievements = achievements
        game.progress_awarded = True

    async def ensure_daily_challenge(self, challenge_date: Optional[date] = None, question_count: int = 5) -> DailyChallenge:
        challenge_date = challenge_date or utcdate()
        async with get_db() as db:
            daily = await db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == challenge_date))
            if daily:
                return daily
            questions = await self._question_pool(db, QuestionCategory.GENERAL, DifficultyLevel.MEDIUM, question_count)
            daily = DailyChallenge(challenge_date=challenge_date, question_count=question_count)
            db.add(daily)
            await db.flush()
            for position, question in enumerate(questions):
                db.add(DailyQuestion(daily_id=daily.id, question_id=question.id, position=position))
            await db.flush()
            return daily

    async def create_daily_game(self, user_id: int, challenge_date: Optional[date] = None) -> Game:
        challenge_date = challenge_date or utcdate()
        async with get_db() as db:
            daily = await self.ensure_daily_challenge_in_session(db, challenge_date, settings.GAME.daily_question_count)
            existing_result = await db.scalar(select(DailyResult).where(
                DailyResult.daily_id == daily.id,
                DailyResult.user_id == user_id,
            ))
            if existing_result:
                raise DailyAlreadyPlayed(existing_result.game_id)
            in_progress = await db.scalar(select(Game).where(
                Game.user_id == user_id,
                Game.mode == GameMode.DAILY.value,
                Game.daily_date == challenge_date,
                Game.status == GameStatus.IN_PROGRESS.value,
            ))
            if in_progress:
                return in_progress
            ids = [row.question_id for row in (await db.execute(
                select(DailyQuestion).where(DailyQuestion.daily_id == daily.id).order_by(DailyQuestion.position)
            )).scalars().all()]
            return await self._new_game(db, user_id, QuestionCategory.GENERAL, DifficultyLevel.MEDIUM,
                                        daily.question_count, GameMode.DAILY, challenge_date, None, ids)

    async def ensure_daily_challenge_in_session(self, db: AsyncSession, challenge_date: date, question_count: int) -> DailyChallenge:
        daily = await db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == challenge_date))
        if daily:
            return daily
        questions = await self._question_pool(db, QuestionCategory.GENERAL, DifficultyLevel.MEDIUM, question_count)
        daily = DailyChallenge(challenge_date=challenge_date, question_count=question_count)
        db.add(daily)
        await db.flush()
        for position, question in enumerate(questions):
            db.add(DailyQuestion(daily_id=daily.id, question_id=question.id, position=position))
        await db.flush()
        return daily

    async def get_daily_status(self, user_id: int, challenge_date: Optional[date] = None) -> Dict[str, Any]:
        challenge_date = challenge_date or utcdate()
        async with get_db() as db:
            daily = await db.scalar(select(DailyChallenge).where(DailyChallenge.challenge_date == challenge_date))
            result = None
            if daily:
                result = await db.scalar(select(DailyResult).where(DailyResult.daily_id == daily.id, DailyResult.user_id == user_id))
            user = await db.get(User, user_id)
            rank = None
            if result and daily:
                results = list((await db.execute(select(DailyResult).where(DailyResult.daily_id == daily.id).order_by(DailyResult.score.desc(), DailyResult.completed_at))).scalars().all())
                rank = next((index + 1 for index, row in enumerate(results) if row.id == result.id), None)
            return {"date": challenge_date, "played": result is not None, "result": result,
                    "rank": rank, "streak": user.daily_streak if user else 0}

    async def create_challenge(self, creator_id: int, category: Any = QuestionCategory.GENERAL,
                               difficulty: Any = DifficultyLevel.MEDIUM, question_count: int = 5,
                               rematch_of: Optional[int] = None) -> tuple[FriendChallenge, Game]:
        async with get_db() as db:
            code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            while await db.scalar(select(FriendChallenge).where(FriendChallenge.code == code)):
                code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            questions = await self._question_pool(db, category, difficulty, question_count)
            challenge = FriendChallenge(code=code, creator_id=creator_id, category=value_of(category),
                                        difficulty=value_of(difficulty), question_count=question_count,
                                        rematch_of=rematch_of, status=ChallengeStatus.IN_PROGRESS.value,
                                        started_at=utcnow())
            db.add(challenge)
            await db.flush()
            ids = []
            for position, question in enumerate(questions):
                ids.append(question.id)
                db.add(ChallengeQuestion(challenge_id=challenge.id, question_id=question.id, position=position))
            game = await self._new_game(db, creator_id, category, difficulty, question_count,
                                        GameMode.CHALLENGE, None, challenge.id, ids)
            db.add(ChallengeAttempt(challenge_id=challenge.id, user_id=creator_id, game_id=game.id))
            await db.flush()
            return challenge, game

    async def join_challenge(self, code: str, user_id: int) -> Game:
        async with get_db() as db:
            challenge = await db.scalar(select(FriendChallenge).where(FriendChallenge.code == code.upper().strip()))
            if not challenge or challenge.status == ChallengeStatus.EXPIRED.value:
                raise ChallengeError("challenge_not_found")
            existing = await db.scalar(select(ChallengeAttempt).where(
                ChallengeAttempt.challenge_id == challenge.id,
                ChallengeAttempt.user_id == user_id,
            ))
            if existing:
                return await db.get(Game, existing.game_id)
            if challenge.opponent_id not in (None, user_id):
                raise ChallengeError("challenge_full")
            if challenge.creator_id == user_id:
                raise ChallengeError("creator_cannot_join")
            challenge.opponent_id = user_id
            challenge.status = ChallengeStatus.IN_PROGRESS.value
            challenge.started_at = challenge.started_at or utcnow()
            ids = [row.question_id for row in (await db.execute(
                select(ChallengeQuestion).where(ChallengeQuestion.challenge_id == challenge.id).order_by(ChallengeQuestion.position)
            )).scalars().all()]
            game = await self._new_game(db, user_id, challenge.category, challenge.difficulty,
                                        challenge.question_count, GameMode.CHALLENGE, None, challenge.id, ids)
            db.add(ChallengeAttempt(challenge_id=challenge.id, user_id=user_id, game_id=game.id))
            await db.flush()
            return game

    async def get_challenge(self, challenge_id: int) -> Optional[FriendChallenge]:
        async with get_db() as db:
            return await db.get(FriendChallenge, challenge_id)

    async def get_challenge_summary(self, challenge_id: int) -> Dict[str, Any]:
        async with get_db() as db:
            challenge = await db.get(FriendChallenge, challenge_id)
            if not challenge:
                return {"found": False}
            attempts = list((await db.execute(select(ChallengeAttempt).where(ChallengeAttempt.challenge_id == challenge_id))).scalars().all())
            return {"found": True, "challenge": challenge, "attempts": attempts,
                    "finished": sum(1 for attempt in attempts if attempt.completed_at is not None) == 2}

    async def get_weekly_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        monday = utcdate() - timedelta(days=utcdate().weekday())
        async with get_db() as db:
            rows = (await db.execute(select(Game, User).join(User, User.id == Game.user_id).where(
                Game.status == GameStatus.COMPLETED.value,
                Game.mode == GameMode.DAILY.value,
                Game.daily_date >= monday,
            ))).all()
            totals: Dict[int, Dict[str, Any]] = {}
            for game, user in rows:
                item = totals.setdefault(user.id, {"user_id": user.id, "name": user.first_name or user.username or str(user.id), "score": 0, "games": 0})
                item["score"] += game.score
                item["games"] += 1
            ranked = sorted(totals.values(), key=lambda item: (-item["score"], -item["games"], item["user_id"]))[:limit]
            for index, item in enumerate(ranked, 1):
                item["rank"] = index
            return ranked

    async def get_random_questions(self, category: Any, difficulty: Any, count: int) -> List[Question]:
        async with get_db() as db:
            return await self._question_pool(db, category, difficulty, count)

    async def update_game_score(self, game_id: int, points: int, is_correct: bool) -> None:
        """Compatibility helper for old integrations; new callbacks use answer_game."""
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if game and game.status == GameStatus.IN_PROGRESS.value:
                game.score += points
                game.correct_answers += int(is_correct)
                if not is_correct:
                    game.lives_remaining -= 1

    async def complete_game(self, game_id: int, score: Optional[int] = None, correct_answers: Optional[int] = None) -> None:
        async with get_db() as db:
            game = await db.get(Game, game_id)
            if game and game.status == GameStatus.IN_PROGRESS.value:
                if score is not None:
                    game.score = score
                if correct_answers is not None:
                    game.correct_answers = correct_answers
                game.status = GameStatus.COMPLETED.value
                game.completed_at = utcnow()
                await self._award_progress(db, game)


db_manager = DatabaseManager()
