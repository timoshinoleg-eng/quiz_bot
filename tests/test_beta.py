from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import db
from config import settings
from http_client import MAX_API_BASE
from keyboards_http import get_answers_keyboard_http, get_question_count_keyboard_http
from models import Base
from models import (
    ChallengeStatus,
    DailyResult,
    GameMode,
    GameStatus,
    Question,
    User,
)


@pytest.fixture
async def database(tmp_path):
    await db.close_db()
    settings.DATABASE = replace(settings.DATABASE, url=f"sqlite+aiosqlite:///{tmp_path / 'beta.sqlite3'}")
    await db.init_db()
    async with db.get_db() as session:
        for index in range(20):
            session.add(Question(
                text=f"Вопрос {index + 1}?",
                category="general",
                difficulty="medium",
                correct_answer=f"Верный {index + 1}",
                wrong_answers=[f"Ошибка {index + 1}A", f"Ошибка {index + 1}B", f"Ошибка {index + 1}C"],
                source="test",
            ))
    yield
    await db.close_db()


async def answer_all(game):
    for _ in range(game.question_count):
        position = game.current_question_index
        current = await db.db_manager.get_current_question(game.id)
        if current is None:
            break
        result = await db.db_manager.answer_game(game.id, game.user_id, position, current.correct_index)
        assert result["ok"]
        game = result["game"]
        if result.get("game_over"):
            break
    return game


@pytest.mark.asyncio
async def test_solo_round_is_immutable_and_duplicate_callback_is_idempotent(database):
    await db.db_manager.get_or_create_user(1, first_name="А")
    game = await db.db_manager.create_game(1, "general", "medium", 5)
    rows = await db.db_manager.get_game_questions(game.id)
    assert [row.position for row in rows] == list(range(5))
    original_ids = [row.question_id for row in rows]

    first = await db.db_manager.answer_game(game.id, 1, 0, rows[0].correct_index)
    duplicate = await db.db_manager.answer_game(game.id, 1, 0, rows[0].correct_index)
    assert first["ok"] and first["correct"]
    assert duplicate["duplicate"] is True
    assert [row.question_id for row in await db.db_manager.get_game_questions(game.id)] == original_ids

    await answer_all(first["game"])
    persisted = await db.db_manager.get_game(game.id)
    assert persisted.status == GameStatus.COMPLETED.value
    assert persisted.answered_questions == 5


@pytest.mark.asyncio
async def test_daily_uses_one_set_and_awards_streak_and_rank(database):
    await db.db_manager.get_or_create_user(1, first_name="А")
    await db.db_manager.get_or_create_user(2, first_name="Б")
    first = await db.db_manager.create_daily_game(1)
    second = await db.db_manager.create_daily_game(2)
    first_ids = [row.question_id for row in await db.db_manager.get_game_questions(first.id)]
    second_ids = [row.question_id for row in await db.db_manager.get_game_questions(second.id)]
    assert first_ids == second_ids

    await answer_all(first)
    status = await db.db_manager.get_daily_status(1, first.daily_date)
    assert status["played"] is True
    assert status["streak"] == 1
    assert status["rank"] == 1
    with pytest.raises(db.DailyAlreadyPlayed) as error:
        await db.db_manager.create_daily_game(1, first.daily_date)
    assert error.value.game_id == first.id


@pytest.mark.asyncio
async def test_friend_challenge_shares_questions_and_completes_after_both_players(database):
    await db.db_manager.get_or_create_user(10, first_name="А")
    await db.db_manager.get_or_create_user(20, first_name="Б")
    challenge, creator_game = await db.db_manager.create_challenge(10, "general", "medium", 5)
    opponent_game = await db.db_manager.join_challenge(challenge.code, 20)
    creator_ids = [row.question_id for row in await db.db_manager.get_game_questions(creator_game.id)]
    opponent_ids = [row.question_id for row in await db.db_manager.get_game_questions(opponent_game.id)]
    assert creator_ids == opponent_ids

    await answer_all(creator_game)
    await answer_all(opponent_game)
    summary = await db.db_manager.get_challenge_summary(challenge.id)
    assert summary["finished"] is True
    stored = await db.db_manager.get_challenge(challenge.id)
    assert stored.status == ChallengeStatus.COMPLETED.value


def test_answer_callback_does_not_leak_correct_index():
    keyboard = get_answers_keyboard_http(["A", "B", "C", "D"], 0, 42, correct_index=3, total_questions=5)
    payloads = [button["payload"] for row in keyboard for button in row if button.get("type") == "callback"]
    assert all(payload.startswith("answer:42:0:") for payload in payloads[:4])
    assert all(len(payload.split(":")) == 4 for payload in payloads[:4])


@pytest.mark.asyncio
async def test_round_lengths_match_available_question_pool(database):
    assert await db.db_manager.available_question_count("general", "medium") == 20
    assert await db.db_manager.available_question_count("sport", "hard") == 0
    keyboard = get_question_count_keyboard_http([5, 10])
    payloads = [button["payload"] for row in keyboard for button in row if button.get("type") == "callback"]
    assert payloads == ["count:5", "count:10", "count:back"]


def test_current_max_endpoint_and_model_tables():
    assert MAX_API_BASE == "https://platform-api2.max.ru"
    required = {"users", "questions", "games", "game_questions", "daily_challenges", "daily_results",
                "friend_challenges", "challenge_questions", "challenge_attempts"}
    assert required.issubset(Base.metadata.tables)


@pytest.mark.asyncio
async def test_max_start_handler_smoke(database):
    import bot

    event = SimpleNamespace(
        message=SimpleNamespace(
            sender=SimpleNamespace(user_id=77, username="tester", first_name="Тест", last_name=None),
            recipient=SimpleNamespace(chat_id=77),
        )
    )
    with patch.object(bot, "send_text", new=AsyncMock()) as send:
        await bot.cmd_start(event)
        assert send.await_count == 1
        assert "Короткая викторина" in send.await_args.args[1]
