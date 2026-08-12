from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
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


def test_answer_keyboard_uses_short_labels_for_long_options():
    keyboard = get_answers_keyboard_http(
        ["Очень длинный вариант ответа " * 10, "Вариант B", "Вариант C", "Вариант D"],
        0,
        42,
        total_questions=10,
    )
    answer_buttons = [button for row in keyboard for button in row if button.get("payload", "").startswith("answer:")]
    assert [button["text"] for button in answer_buttons] == ["🔵 A", "🟢 B", "🟡 C", "🔴 D"]


def test_achievement_codes_have_player_facing_labels():
    import bot

    assert bot.format_achievements(["first_game", "perfect"]) == "🎮 Первый раунд, 💎 Идеальный раунд"


@pytest.mark.asyncio
async def test_share_result_sends_native_max_share_card():
    import bot

    game = SimpleNamespace(id=8, user_id=7, status="completed", score=420, correct_answers=4, question_count=5)
    fake_bot = SimpleNamespace(send_message=AsyncMock())
    with patch.object(bot.db_manager, "get_game", new=AsyncMock(return_value=game)), patch.object(bot, "bot", fake_bot), patch.object(bot, "MAXAPI_AVAILABLE", True):
        await bot.share_game_result(70, 7, 8)

    sent = fake_bot.send_message.await_args.kwargs
    assert sent["chat_id"] == 70
    assert sent["attachments"][0].type == "share"
    assert sent["attachments"][0].description == "🏆 Я набрал 420 очков в Quiz Battle — 4/5 (80%)!"


@pytest.mark.asyncio
async def test_timer_message_uses_editable_max_message_id():
    import bot

    bot.bot = SimpleNamespace(
        send_message=AsyncMock(
            return_value=SimpleNamespace(
                message=SimpleNamespace(body=SimpleNamespace(mid="timer-123"))
            )
        )
    )
    message_id = await bot._send_timer_message(77, 30)
    assert message_id == "timer-123"
    bot.bot.send_message.assert_awaited_once_with(chat_id=77, text="⏱ Осталось времени: 30 сек.")


@pytest.mark.asyncio
async def test_round_lengths_match_available_question_pool(database):
    assert await db.db_manager.available_question_count("general", "medium") == 20
    assert await db.db_manager.available_question_count("sport", "hard") == 0
    keyboard = get_question_count_keyboard_http([5, 10])
    payloads = [button["payload"] for row in keyboard for button in row if button.get("type") == "callback"]
    assert payloads == ["count:5", "count:10", "count:back"]


@pytest.mark.asyncio
async def test_wrong_answers_do_not_truncate_selected_round(database):
    await db.db_manager.get_or_create_user(101, first_name="Раунд")
    game = await db.db_manager.create_game(101, "general", "medium", 10)
    for position in range(9):
        current = await db.db_manager.get_current_question(game.id)
        result = await db.db_manager.answer_game(game.id, 101, position, -1)
        assert result["ok"] and result["game_over"] is False
        assert current is not None
        game = result["game"]
    final = await db.db_manager.answer_game(game.id, 101, 9, -1)
    assert final["ok"] and final["game_over"] is True
    assert final["game"].question_count == 10
    assert final["game"].answered_questions == 10


@pytest.mark.asyncio
async def test_answer_after_timeout_is_rejected_as_timed_out(database):
    await db.db_manager.get_or_create_user(102, first_name="Таймер")
    game = await db.db_manager.create_game(102, "general", "medium", 5)
    async with db.get_db() as session:
        row = (await session.execute(
            db.select(db.GameQuestion).where(
                db.GameQuestion.game_id == game.id,
                db.GameQuestion.position == 0,
            )
        )).scalar_one()
        row.sent_at = db.utcnow() - timedelta(seconds=31)
    current = await db.db_manager.get_current_question(game.id)
    result = await db.db_manager.answer_game(game.id, 102, 0, current.correct_index)
    assert result["ok"] and result["timed_out"] is True
    assert result["correct"] is False
    assert result["points"] == 0


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
