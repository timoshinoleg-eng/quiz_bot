"""Persistent domain model for the MAX Quiz Battle beta.

The database is the source of truth for every round.  In particular, the
answer options and the correct option index are stored on ``GameQuestion``;
callbacks only contain the game id, position and the selected index.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionCategory(str, enum.Enum):
    HISTORY = "history"
    SCIENCE = "science"
    ART = "art"
    SPORT = "sport"
    GEOGRAPHY = "geography"
    ENTERTAINMENT = "entertainment"
    GENERAL = "general"


class GameMode(str, enum.Enum):
    SOLO = "solo"
    DAILY = "daily"
    CHALLENGE = "challenge"


class GameStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ChallengeStatus(str, enum.Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    score_total = Column(Integer, nullable=False, default=0, server_default="0")
    games_played = Column(Integer, nullable=False, default=0, server_default="0")
    games_won = Column(Integer, nullable=False, default=0, server_default="0")
    xp = Column(Integer, nullable=False, default=0, server_default="0")
    level = Column(Integer, nullable=False, default=1, server_default="1")
    daily_streak = Column(Integer, nullable=False, default=0, server_default="0")
    best_streak = Column(Integer, nullable=False, default=0, server_default="0")
    last_daily_date = Column(Date, nullable=True)
    achievements = Column(JSON, nullable=False, default=list, server_default="[]")
    current_state = Column(String(50), nullable=True)
    state_data = Column(JSON, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    games = relationship("Game", back_populates="user")
    daily_results = relationship("DailyResult", back_populates="user")
    challenge_attempts = relationship("ChallengeAttempt", back_populates="user")
    question_history = relationship("UserQuestionHistory", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    category = Column(String(32), nullable=False, index=True)
    difficulty = Column(String(16), nullable=False, index=True)
    correct_answer = Column(Text, nullable=False)
    wrong_answers = Column(JSON, nullable=False)
    explanation = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, default="seed")
    source_id = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    source_license = Column(String(120), nullable=False, default="CC0-1.0")
    language = Column(String(8), nullable=False, default="ru", server_default="ru", index=True)
    tags = Column(JSON, nullable=False, default=list, server_default="[]")
    age_min = Column(Integer, nullable=False, default=10, server_default="10")
    age_max = Column(Integer, nullable=False, default=14, server_default="14")
    verified = Column(Boolean, nullable=False, default=False, server_default="0", index=True)
    content_rating = Column(String(16), nullable=False, default="kids", server_default="kids")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    usage_count = Column(Integer, nullable=False, default=0, server_default="0")
    correct_rate = Column(Float, nullable=False, default=0.0, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    game_questions = relationship("GameQuestion", back_populates="question")
    packs = relationship("QuizPack", secondary="quiz_pack_questions", back_populates="questions")
    history = relationship("UserQuestionHistory", back_populates="question", cascade="all, delete-orphan")


class QuizPack(Base):
    __tablename__ = "quiz_packs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(160), nullable=False)
    short_description = Column(String(280), nullable=False)
    description = Column(Text, nullable=False)
    emoji = Column(String(16), nullable=False)
    category = Column(String(32), nullable=False, index=True)
    language = Column(String(8), nullable=False, default="ru", server_default="ru")
    age_min = Column(Integer, nullable=False, default=10, server_default="10")
    age_max = Column(Integer, nullable=False, default=14, server_default="14")
    featured = Column(Boolean, nullable=False, default=False, server_default="0", index=True)
    active = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    estimated_minutes = Column(Integer, nullable=False, default=2, server_default="2")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    questions = relationship("Question", secondary="quiz_pack_questions", back_populates="packs")


class QuizPackQuestion(Base):
    __tablename__ = "quiz_pack_questions"
    __table_args__ = (UniqueConstraint("quiz_pack_id", "question_id", name="uq_quiz_pack_question"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_pack_id = Column(Integer, ForeignKey("quiz_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)


class UserQuestionHistory(Base):
    __tablename__ = "user_question_history"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_user_question_history"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    times_seen = Column(Integer, nullable=False, default=0, server_default="0")
    times_correct = Column(Integer, nullable=False, default=0, server_default="0")
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_is_correct = Column(Boolean, nullable=True)

    user = relationship("User", back_populates="question_history")
    question = relationship("Question", back_populates="history")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String(16), nullable=False, default=GameMode.SOLO.value, index=True)
    category = Column(String(32), nullable=False, default=QuestionCategory.GENERAL.value)
    difficulty = Column(String(16), nullable=False, default=DifficultyLevel.MEDIUM.value)
    question_count = Column(Integer, nullable=False, default=5)
    status = Column(String(16), nullable=False, default=GameStatus.IN_PROGRESS.value, index=True)
    current_question_index = Column(Integer, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    answered_questions = Column(Integer, nullable=False, default=0)
    lives_remaining = Column(Integer, nullable=False, default=3)
    daily_date = Column(Date, nullable=True, index=True)
    challenge_id = Column(Integer, ForeignKey("friend_challenges.id"), nullable=True, index=True)
    progress_awarded = Column(Boolean, nullable=False, default=False, server_default="0")
    finished_reason = Column(String(32), nullable=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="games")
    questions = relationship("GameQuestion", back_populates="game", cascade="all, delete-orphan", order_by="GameQuestion.position")
    challenge = relationship("FriendChallenge", back_populates="games", foreign_keys=[challenge_id])


class GameQuestion(Base):
    __tablename__ = "game_questions"
    __table_args__ = (UniqueConstraint("game_id", "position", name="uq_game_question_position"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    position = Column(Integer, nullable=False)
    answer_options = Column(JSON, nullable=False)
    correct_index = Column(Integer, nullable=False)
    was_answered = Column(Boolean, nullable=False, default=False, server_default="0")
    selected_index = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answer_time = Column(Float, nullable=True)
    points_earned = Column(Integer, nullable=False, default=0, server_default="0")
    sent_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    game = relationship("Game", back_populates="questions")
    question = relationship("Question", back_populates="game_questions")


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_date = Column(Date, nullable=False, unique=True, index=True)
    question_count = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    questions = relationship("DailyQuestion", back_populates="daily", cascade="all, delete-orphan", order_by="DailyQuestion.position")
    results = relationship("DailyResult", back_populates="daily", cascade="all, delete-orphan")


class DailyQuestion(Base):
    __tablename__ = "daily_questions"
    __table_args__ = (UniqueConstraint("daily_id", "position", name="uq_daily_question_position"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_id = Column(Integer, ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    position = Column(Integer, nullable=False)

    daily = relationship("DailyChallenge", back_populates="questions")
    question = relationship("Question")


class DailyResult(Base):
    __tablename__ = "daily_results"
    __table_args__ = (UniqueConstraint("daily_id", "user_id", name="uq_daily_result_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_id = Column(Integer, ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=False, server_default=func.now())

    daily = relationship("DailyChallenge", back_populates="results")
    user = relationship("User", back_populates="daily_results")


class FriendChallenge(Base):
    __tablename__ = "friend_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    creator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    opponent_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    category = Column(String(32), nullable=False, default=QuestionCategory.GENERAL.value)
    difficulty = Column(String(16), nullable=False, default=DifficultyLevel.MEDIUM.value)
    question_count = Column(Integer, nullable=False, default=5)
    status = Column(String(16), nullable=False, default=ChallengeStatus.WAITING.value, index=True)
    rematch_of = Column(Integer, ForeignKey("friend_challenges.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    games = relationship("Game", back_populates="challenge", foreign_keys="Game.challenge_id")
    questions = relationship("ChallengeQuestion", back_populates="challenge", cascade="all, delete-orphan", order_by="ChallengeQuestion.position")
    attempts = relationship("ChallengeAttempt", back_populates="challenge", cascade="all, delete-orphan")


class ChallengeQuestion(Base):
    __tablename__ = "challenge_questions"
    __table_args__ = (UniqueConstraint("challenge_id", "position", name="uq_challenge_question_position"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(Integer, ForeignKey("friend_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    position = Column(Integer, nullable=False)

    challenge = relationship("FriendChallenge", back_populates="questions")
    question = relationship("Question")


class ChallengeAttempt(Base):
    __tablename__ = "challenge_attempts"
    __table_args__ = (UniqueConstraint("challenge_id", "user_id", name="uq_challenge_attempt_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(Integer, ForeignKey("friend_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)

    challenge = relationship("FriendChallenge", back_populates="attempts")
    user = relationship("User", back_populates="challenge_attempts")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
