"""MAX transport handlers for Quiz Battle beta.

Handlers only translate MAX events into application-service calls.  Game rules,
idempotency and persistence live in :mod:`db` and do not depend on MAX.
"""

from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Any, Optional
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()


def configure_logging() -> None:
    """Configure console and rotating file logs for live MAX diagnostics."""
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_dir / "quiz_bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        handlers=[file_handler, console_handler],
        force=True,
    )


configure_logging()
logger = logging.getLogger("quiz_bot")

try:
    from maxapi import Bot, Dispatcher
    from maxapi.types import BotStarted, Command, MessageCallback, MessageCreated, ShareAttachmentPayload
    from maxapi.types.attachments import Share
    MAXAPI_AVAILABLE = True
except ImportError:
    MAXAPI_AVAILABLE = False

    class MockBot:
        def __init__(self, token: Optional[str] = None):
            self.token = token

        async def send_message(self, chat_id: int, text: str, attachments=None, **kwargs):
            logger.info("[MOCK] chat=%s %s", chat_id, text.replace("\n", " ")[:120])

        async def delete_webhook(self):
            return None

    class MockDispatcher:
        def bot_started(self):
            return lambda function: function

        def message_created(self, *args, **kwargs):
            return lambda function: function

        def message_callback(self):
            return lambda function: function

        async def start_polling(self, bot):
            raise RuntimeError("maxapi is not installed; install requirements.txt before polling")

    Bot, Dispatcher = MockBot, MockDispatcher
    BotStarted = MessageCreated = MessageCallback = object
    Command = lambda *args, **kwargs: object()
    Share = ShareAttachmentPayload = None


class NoTokenBot:
    """Import-safe bot used for tests and static checks without secrets."""

    def __init__(self, token: Optional[str] = None):
        self.token = token

    async def send_message(self, chat_id: int, text: str, attachments=None, **kwargs):
        logger.info("[NO TOKEN] chat=%s %s", chat_id, text.replace("\n", " ")[:120])

    async def delete_webhook(self):
        return None

from config import settings
from db import (
    ChallengeError,
    DailyAlreadyPlayed,
    db_manager,
    init_db,
    close_db,
)
from keyboards_http import (
    get_answers_keyboard_http,
    get_challenge_keyboard_http,
    get_difficulty_keyboard_http,
    get_game_over_keyboard_http,
    get_main_menu_keyboard_http,
    get_question_count_keyboard_http,
    get_topics_keyboard_http,
)
from keyboard_adapter import KeyboardAdapter
from models import DifficultyLevel, GameMode, QuestionCategory
from states import State, get_context
from services.challenges import create as create_challenge
from services.profile import weekly_leaderboard

try:
    from http_client import MaxHttpClient
except ImportError:
    MaxHttpClient = None


bot = Bot(token=settings.BOT.token) if settings.BOT.token else NoTokenBot()
dp = Dispatcher()
http_client = MaxHttpClient(settings.BOT.token) if MaxHttpClient and settings.BOT.token else None
keyboard_adapter = KeyboardAdapter(bot=bot, http_client=http_client, prefer_http=bool(http_client))
_question_timeout_tasks: dict[tuple[int, int], asyncio.Task[Any]] = {}
_question_timer_messages: dict[tuple[int, int], str] = {}
logger.info(
    "runtime_initialized maxapi_available=%s http_client=%s bot_username=%s",
    MAXAPI_AVAILABLE,
    bool(http_client),
    settings.BOT.username or "unset",
)

ACHIEVEMENT_LABELS = {
    "first_game": "🎮 Первый раунд",
    "perfect": "💎 Идеальный раунд",
    "streak_3": "🔥 Серия 3 дня",
    "streak_7": "⚡ Серия 7 дней",
}


def _get_nested(event: Any, *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value = event
        try:
            for part in path:
                value = getattr(value, part)
            if value is not None:
                return value
        except (AttributeError, TypeError):
            continue
    return None


def get_user_id_from_event(event: Any) -> int:
    value = _get_nested(event, ("callback", "user", "user_id"), ("message", "sender", "user_id"), ("from_user", "id"))
    if value is None:
        raise ValueError("Cannot extract user_id from MAX event")
    return int(value)


def get_chat_id_from_event(event: Any) -> int:
    value = _get_nested(event, ("chat", "chat_id"), ("message", "recipient", "chat_id"), ("message", "chat", "id"), ("chat_id",))
    if value is None:
        raise ValueError("Cannot extract chat_id from MAX event")
    return int(value)


def get_user_name_from_event(event: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    user = _get_nested(event, ("callback", "user"), ("message", "sender"), ("from_user",))
    return (
        getattr(user, "username", None) if user else None,
        getattr(user, "first_name", None) if user else None,
        getattr(user, "last_name", None) if user else None,
    )


def callback_payload(event: Any) -> str:
    return str(_get_nested(event, ("callback", "payload"), ("data",)) or "")


def event_text(event: Any) -> str:
    return str(_get_nested(event, ("message", "body", "text"), ("message", "text"), ("text",)) or "")


async def acknowledge(event: Any) -> None:
    callback_id = _get_nested(event, ("callback", "callback_id"))
    if callback_id and http_client:
        try:
            result = await http_client.answer_callback_query(str(callback_id))
            logger.info(
                "callback_ack success=%s status=%s error=%s",
                result.success,
                result.status_code,
                result.error_message or "-",
            )
            if result.success:
                return
        except Exception:
            logger.warning("callback_ack request failed", exc_info=True)
    answer = getattr(event, "answer", None)
    if answer:
        try:
            await answer()
        except Exception:
            logger.debug("MAX callback acknowledgement fallback failed", exc_info=True)


async def send_text(chat_id: int, text: str, buttons=None) -> None:
    payloads = [
        str(button.get("payload", ""))
        for row in (buttons or [])
        for button in row
        if isinstance(button, dict)
    ]
    logger.info(
        "outbound_message chat_id=%s text_preview=%r button_count=%s payloads=%s",
        chat_id,
        text.replace("\n", " ")[:100],
        len(payloads),
        payloads,
    )
    if buttons:
        sent = await keyboard_adapter.send_with_keyboard(chat_id=chat_id, text=text, buttons=buttons)
        logger.info("keyboard_delivery chat_id=%s success=%s", chat_id, sent)
        if sent:
            return
        logger.warning("keyboard_delivery_failed chat_id=%s fallback=plain_message", chat_id)
    await bot.send_message(chat_id=chat_id, text=text)


async def send_menu(chat_id: int, title: str = "🏠 Главное меню") -> None:
    await send_text(chat_id, title, get_main_menu_keyboard_http(mini_app_url=settings.MINI_APP_URL))


def format_achievements(achievements: list[str] | None) -> str:
    return ", ".join(ACHIEVEMENT_LABELS.get(code, f"🏅 {code.replace('_', ' ')}") for code in (achievements or [])) or "пока нет"


async def share_game_result(chat_id: int, user_id: int, game_id: int) -> None:
    """Send a native MAX share card for a completed game owned by the caller."""
    game = await db_manager.get_game(game_id)
    if not game or game.user_id != user_id or game.status != "completed":
        await send_text(chat_id, "Этот результат уже недоступен. Сыграй новый раунд!")
        return
    accuracy = round(game.correct_answers / max(1, game.question_count) * 100)
    text = f"🏆 Я набрал {game.score} очков в Quiz Battle — {game.correct_answers}/{game.question_count} ({accuracy}%)!"
    link = f"https://max.ru/{settings.BOT.username}" if settings.BOT.username else None
    if MAXAPI_AVAILABLE and Share is not None:
        try:
            attachment = Share(
                type="share",
                title="Quiz Battle",
                description=text,
                payload=ShareAttachmentPayload(url=link) if link else ShareAttachmentPayload(),
            )
            await bot.send_message(chat_id=chat_id, text="📤 Нажми на карточку, чтобы поделиться результатом.", attachments=[attachment])
            logger.info("share_card_sent chat_id=%s user_id=%s game_id=%s", chat_id, user_id, game_id)
            return
        except Exception:
            logger.exception("share_card_send_failed chat_id=%s user_id=%s game_id=%s", chat_id, user_id, game_id)
    await bot.send_message(chat_id=chat_id, text=f"{text}\n{link}" if link else text)


async def send_question(chat_id: int, game_id: int) -> None:
    game = await db_manager.get_game(game_id)
    question = await db_manager.get_current_question(game_id)
    if not game or not question:
        logger.warning("question_unavailable chat_id=%s game_id=%s", chat_id, game_id)
        await send_menu(chat_id, "Игра уже завершена. Выбери следующий режим:")
        return
    logger.info(
        "question_sent chat_id=%s game_id=%s position=%s total=%s",
        chat_id,
        game_id,
        question.position,
        game.question_count,
    )
    text = (
        f"❓ Вопрос {question.position + 1}/{game.question_count}\n\n"
        f"{question.question.text}\n\n"
        "Варианты ответа:\n"
        + "\n".join(
            f"{chr(65 + index)}. {answer}"
            for index, answer in enumerate(question.answer_options[:4])
        )
        + "\n\n"
        f"⏱ У тебя {settings.GAME.answer_timeout} секунд"
    )
    buttons = get_answers_keyboard_http(question.answer_options, question.position, game_id,
                                        total_questions=game.question_count)
    await send_text(chat_id, text, buttons)
    timer_message_id = await _send_timer_message(chat_id, settings.GAME.answer_timeout)
    _schedule_question_timeout(chat_id, game.user_id, game.id, question.position, timer_message_id)


async def _send_timer_message(chat_id: int, timeout: int) -> Optional[str]:
    """Send a separate editable countdown message and return its MAX message id."""
    try:
        result = await bot.send_message(
            chat_id=chat_id,
            text=f"⏱ Осталось времени: {timeout} сек.",
        )
        body = getattr(getattr(result, "message", None), "body", None)
        message_id = getattr(body, "mid", None)
        if message_id is None and isinstance(result, dict):
            message_id = (
                result.get("message", {}).get("body", {}).get("mid")
                or result.get("message", {}).get("mid")
                or result.get("mid")
            )
        if message_id is None:
            logger.warning("timer_message_id_missing chat_id=%s", chat_id)
            return None
        logger.info("timer_message_sent chat_id=%s message_id=%s timeout=%s", chat_id, message_id, timeout)
        return str(message_id)
    except Exception:
        logger.exception("timer_message_send_failed chat_id=%s", chat_id)
        return None


def _cancel_question_timeout(game_id: int, position: int) -> None:
    task = _question_timeout_tasks.pop((game_id, position), None)
    if task and task is not asyncio.current_task() and not task.done():
        task.cancel()


def _schedule_question_timeout(
    chat_id: int,
    user_id: int,
    game_id: int,
    position: int,
    timer_message_id: Optional[str],
) -> None:
    _cancel_question_timeout(game_id, position)
    if timer_message_id:
        _question_timer_messages[(game_id, position)] = timer_message_id
    task = asyncio.create_task(
        _expire_question(chat_id, user_id, game_id, position, timer_message_id)
    )
    _question_timeout_tasks[(game_id, position)] = task


async def _expire_question(
    chat_id: int,
    user_id: int,
    game_id: int,
    position: int,
    timer_message_id: Optional[str],
) -> None:
    timeout = settings.GAME.answer_timeout
    try:
        deadline = asyncio.get_running_loop().time() + timeout
        remaining = timeout
        while remaining > 0:
            await asyncio.sleep(min(5, remaining))
            remaining = max(0, int(deadline - asyncio.get_running_loop().time() + 0.999))
            if timer_message_id and remaining > 0:
                try:
                    await bot.edit_message(
                        message_id=timer_message_id,
                        text=f"⏱ Осталось времени: {remaining} сек.",
                    )
                    logger.info(
                        "timer_message_updated message_id=%s remaining=%s",
                        timer_message_id,
                        remaining,
                    )
                except Exception:
                    logger.exception(
                        "timer_message_update_failed message_id=%s remaining=%s",
                        timer_message_id,
                        remaining,
                    )
        result = await db_manager.answer_game(game_id, user_id, position, -1, timeout)
        if not result.get("ok") or result.get("duplicate"):
            return
        logger.info(
            "question_timeout game_id=%s position=%s next=%s",
            game_id,
            position,
            not result.get("game_over"),
        )
        game = result["game"]
        await _update_timer_message(game_id, position, "⏰ Время вышло")
        if result.get("game_over"):
            await finish_message(chat_id, game)
            return
        await send_text(chat_id, "⏰ Время вышло. Ответ не засчитан.")
        await send_question(chat_id, game.id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("question_timeout_failed game_id=%s position=%s", game_id, position)
    finally:
        current = _question_timeout_tasks.get((game_id, position))
        if current is asyncio.current_task():
            _question_timeout_tasks.pop((game_id, position), None)
        _question_timer_messages.pop((game_id, position), None)


async def _update_timer_message(game_id: int, position: int, text: str) -> None:
    message_id = _question_timer_messages.get((game_id, position))
    if not message_id:
        return
    try:
        await bot.edit_message(message_id=message_id, text=text)
        logger.info("timer_message_updated message_id=%s text=%r", message_id, text)
    except Exception:
        logger.exception("timer_message_update_failed message_id=%s text=%r", message_id, text)


def _cancel_all_question_timeouts() -> None:
    for game_id, position in list(_question_timeout_tasks):
        _cancel_question_timeout(game_id, position)
    _question_timer_messages.clear()


def _result_text(game: Any, prefix: str = "🏆 Результат") -> str:
    accuracy = (game.correct_answers / game.question_count * 100) if game.question_count else 0
    return (
        f"{prefix}\n\n"
        f"✅ {game.correct_answers}/{game.question_count} правильно\n"
        f"⚡ {game.score} очков\n"
        f"🎯 Точность: {accuracy:.0f}%\n"
        f"⭐ Прогресс сохранён"
    )


async def finish_message(chat_id: int, game: Any) -> None:
    if game.mode == GameMode.DAILY.value:
        status = await db_manager.get_daily_status(game.user_id, game.daily_date)
        prefix = f"🎯 Сегодня: {game.correct_answers}/{game.question_count}\n🔥 Серия: {status['streak']}"
        if status.get("rank"):
            prefix += f"\n🏆 Место: #{status['rank']}"
        text = _result_text(game, prefix)
    elif game.mode == GameMode.CHALLENGE.value and game.challenge_id:
        summary = await db_manager.get_challenge_summary(game.challenge_id)
        text = _result_text(game, "⚔️ Вызов принят\n\nРезультат сохранён")
        if summary.get("finished"):
            attempts = sorted(summary["attempts"], key=lambda item: item.score, reverse=True)
            text += "\n\n🏁 Оба игрока завершили игру!"
            if len(attempts) == 2:
                text += f"\nСчёт: {attempts[0].score} — {attempts[1].score}"
        else:
            text += "\n\nЖдём соперника."
        await send_text(chat_id, text, get_challenge_keyboard_http(game.challenge_id))
        return
    else:
        text = _result_text(game)
    await send_text(chat_id, text, get_game_over_keyboard_http(game.id, game.correct_answers, game.question_count))


async def start_solo(chat_id: int, user_id: int) -> None:
    state = await get_context(user_id)
    await state.set_state(State.SELECT_TOPIC)
    await send_text(chat_id, "🎮 Быстрая игра\n\nВыбери тему:", get_topics_keyboard_http())


async def start_daily(chat_id: int, user_id: int) -> None:
    try:
        game = await db_manager.create_daily_game(user_id)
    except DailyAlreadyPlayed as exc:
        game = await db_manager.get_game(exc.game_id)
        if game is None:
            logger.error("daily_completed_game_missing game_id=%s user_id=%s", exc.game_id, user_id)
            await send_text(chat_id, "Сегодняшний результат не найден. Нажми /start")
            return
        await finish_message(chat_id, game)
        return
    state = await get_context(user_id)
    await state.update_data(game_id=game.id, mode=GameMode.DAILY.value)
    await state.set_state(State.IN_GAME)
    await send_question(chat_id, game.id)


async def invite_challenge(chat_id: int, user_id: int, category: str = "general", difficulty: str = "medium") -> None:
    challenge, game = await create_challenge(user_id, category, difficulty, settings.GAME.challenge_question_count)
    bot_name = settings.BOT.username
    link = f"https://max.ru/{bot_name}?start=challenge_{quote(challenge.code)}" if bot_name else None
    invite = f"⚔️ Вызов создан!\n\nКод: `{challenge.code}`\nОтправь его другу в MAX."
    if link:
        invite += f"\n\nОткрыть вызов: {link}"
    await send_text(chat_id, invite)
    state = await get_context(user_id)
    await state.update_data(game_id=game.id, mode=GameMode.CHALLENGE.value)
    await state.set_state(State.IN_GAME)
    await send_question(chat_id, game.id)


async def join_challenge(chat_id: int, user_id: int, code: str) -> None:
    try:
        game = await db_manager.join_challenge(code, user_id)
    except ChallengeError as exc:
        messages = {
            "challenge_not_found": "Вызов не найден или уже истёк.",
            "challenge_full": "Этот вызов уже принят другим игроком.",
            "creator_cannot_join": "Ты уже играешь в этот вызов.",
        }
        await send_text(chat_id, messages.get(str(exc), "Не удалось открыть вызов.") + "\n\n🏠 Нажми /start")
        return
    state = await get_context(user_id)
    await state.update_data(game_id=game.id, mode=GameMode.CHALLENGE.value)
    await state.set_state(State.IN_GAME)
    await send_question(chat_id, game.id)


async def handle_start_payload(event: Any, payload: Optional[str]) -> None:
    if payload and payload.startswith("challenge_"):
        await join_challenge(get_chat_id_from_event(event), get_user_id_from_event(event), payload[10:])


@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    payload = _get_nested(event, ("payload",))
    if payload:
        await handle_start_payload(event, payload)
    else:
        await send_text(get_chat_id_from_event(event), "🎯 Добро пожаловать в Quiz Battle! Нажми /start")


@dp.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    username, first_name, last_name = get_user_name_from_event(event)
    user = await db_manager.get_or_create_user(user_id, username, first_name, last_name)
    payload = _get_nested(event, ("payload",), ("message", "body", "payload"))
    if payload:
        await handle_start_payload(event, payload)
        return
    await send_text(
        chat_id,
        f"Привет, {user.first_name or user.username or 'друг'}!\n\n"
        "🎯 Короткая викторина для игры с друзьями.\n"
        "Один Daily в день, XP и реванши.\n\nВыбирай режим:",
        get_main_menu_keyboard_http(),
    )


@dp.message_created(Command("play"))
async def cmd_play(event: MessageCreated):
    await start_solo(get_chat_id_from_event(event), get_user_id_from_event(event))


@dp.message_created(Command("daily"))
async def cmd_daily(event: MessageCreated):
    await start_daily(get_chat_id_from_event(event), get_user_id_from_event(event))


@dp.message_created(Command("challenge"))
async def cmd_challenge(event: MessageCreated):
    await invite_challenge(get_chat_id_from_event(event), get_user_id_from_event(event))


@dp.message_created(Command("join"))
async def cmd_join(event: MessageCreated):
    parts = event_text(event).split(maxsplit=1)
    if len(parts) != 2:
        await send_text(get_chat_id_from_event(event), "Используй: /join КОД_ВЫЗОВА")
        return
    await join_challenge(get_chat_id_from_event(event), get_user_id_from_event(event), parts[1])


@dp.message_created(Command("stats"))
async def cmd_stats(event: MessageCreated):
    user = await db_manager.get_or_create_user(get_user_id_from_event(event))
    achievements = format_achievements(user.achievements)
    await send_text(get_chat_id_from_event(event),
                    f"👤 Профиль\n\n⭐ XP: {user.xp}\n🎚 Уровень: {user.level}\n"
                    f"🎮 Игр: {user.games_played}\n🏆 Побед: {user.games_won}\n"
                    f"🔥 Лучшая серия: {user.best_streak}\n🎖 Достижения: {achievements}")


@dp.message_created(Command("leaderboard"))
async def cmd_leaderboard(event: MessageCreated):
    await show_leaderboard(get_chat_id_from_event(event))


@dp.message_created(Command("help"))
async def cmd_help(event: MessageCreated):
    await send_text(get_chat_id_from_event(event),
                    "❓ Помощь\n\n/start — меню\n/daily — общий вопрос дня\n"
                    "/play — быстрая игра\n/challenge — вызвать друга\n"
                    "/join КОД — принять вызов\n/stats — профиль\n/leaderboard — рейтинг")


async def show_leaderboard(chat_id: int) -> None:
    rows = await weekly_leaderboard(10)
    if not rows:
        await send_text(chat_id, "🏆 Рейтинг\n\nПока никто не сыграл Daily. Будь первым!")
        return
    lines = ["🏆 Рейтинг недели\n"]
    lines.extend(f"{row['rank']}. {row['name']} — {row['score']} ⚡" for row in rows)
    await send_text(chat_id, "\n".join(lines))


@dp.message_callback()
async def handle_callback(event: MessageCallback):
    payload = callback_payload(event)
    try:
        user_id = get_user_id_from_event(event)
        chat_id = get_chat_id_from_event(event)
    except Exception:
        logger.exception(
            "callback_context_failed event_type=%s payload=%s",
            type(event).__name__,
            payload,
        )
        raise
    logger.info(
        "callback_received payload=%s user_id=%s chat_id=%s",
        payload,
        user_id,
        chat_id,
    )
    await acknowledge(event)
    try:
        if payload == "menu:daily":
            await start_daily(chat_id, user_id)
        elif payload == "menu:challenge":
            await invite_challenge(chat_id, user_id)
        elif payload == "menu:play":
            await start_solo(chat_id, user_id)
        elif payload in ("menu:profile", "menu:stats"):
            await cmd_stats(event)
        elif payload == "menu:leaderboard":
            await show_leaderboard(chat_id)
        elif payload == "menu:help":
            await cmd_help(event)
        elif payload == "menu:back":
            await send_menu(chat_id)
        elif payload.startswith("topic:"):
            await select_topic(user_id, chat_id, payload.split(":", 1)[1])
        elif payload.startswith("difficulty:"):
            await select_difficulty(user_id, chat_id, payload.split(":", 1)[1])
        elif payload.startswith("count:"):
            await select_count(user_id, chat_id, payload.split(":", 1)[1])
        elif payload.startswith("answer:"):
            await answer_callback(user_id, chat_id, payload)
        elif payload.startswith("skip:"):
            await answer_callback(user_id, chat_id, payload.replace("skip:", "answer:") + ":-1")
        elif payload.startswith("share:"):
            try:
                await share_game_result(chat_id, user_id, int(payload.split(":", 1)[1]))
            except ValueError:
                await send_text(chat_id, "Не удалось определить результат для публикации.")
        elif payload.startswith("challenge:rematch:"):
            old = await db_manager.get_challenge(int(payload.rsplit(":", 1)[1]))
            if old:
                await invite_challenge(chat_id, user_id, old.category, old.difficulty)
        else:
            await send_text(chat_id, "Эта кнопка устарела. Нажми /start")
        logger.info(
            "callback_handled payload=%s user_id=%s chat_id=%s",
            payload,
            user_id,
            chat_id,
        )
    except Exception:
        logger.exception("Unhandled callback payload=%s", payload)
        await send_text(chat_id, "Что-то пошло не так. Попробуй ещё раз.", get_main_menu_keyboard_http())


async def select_topic(user_id: int, chat_id: int, topic: str) -> None:
    if topic == "back":
        await send_menu(chat_id)
        return
    state = await get_context(user_id)
    await state.update_data(selected_topic=topic)
    await state.set_state(State.SELECT_DIFFICULTY)
    await send_text(chat_id, "🎯 Тема выбрана.\n\nВыбери сложность:", get_difficulty_keyboard_http())


async def select_difficulty(user_id: int, chat_id: int, difficulty: str) -> None:
    if difficulty == "back":
        await start_solo(chat_id, user_id)
        return
    state = await get_context(user_id)
    await state.update_data(selected_difficulty=difficulty)
    await state.set_state(State.SELECT_QUESTION_COUNT)
    data = await state.get_data()
    available_count = await db_manager.available_question_count(data.get("selected_topic", "general"), difficulty)
    available_counts = [count for count in settings.GAME.question_options if count <= available_count]
    if not available_counts:
        await send_text(chat_id, "Для этой темы пока недостаточно вопросов. Выбери другую тему.", get_topics_keyboard_http())
        await state.set_state(State.SELECT_TOPIC)
        return
    await send_text(chat_id, "⚙️ Выбери длину раунда:", get_question_count_keyboard_http(available_counts))


async def select_count(user_id: int, chat_id: int, count_text: str) -> None:
    if count_text == "back":
        await select_topic(user_id, chat_id, "back")
        return
    try:
        count = int(count_text)
    except ValueError:
        await send_text(chat_id, "Некорректная длина раунда. Выбери вариант кнопкой.")
        return
    state = await get_context(user_id)
    data = await state.get_data()
    topic = data.get("selected_topic", "general")
    difficulty = data.get("selected_difficulty", "medium")
    available_count = await db_manager.available_question_count(topic, difficulty)
    available_counts = [option for option in settings.GAME.question_options if option <= available_count]
    if count not in available_counts:
        await send_text(chat_id, "Этот размер пока недоступен для выбранной темы.",
                        get_question_count_keyboard_http(available_counts))
        return
    try:
        game = await db_manager.create_game(user_id, topic, difficulty, count)
    except ValueError:
        logger.warning("game_creation_pool_changed user_id=%s topic=%s difficulty=%s count=%s", user_id, topic, difficulty, count)
        await send_text(chat_id, "Набор вопросов обновился. Выбери доступную длину ещё раз.",
                        get_question_count_keyboard_http(available_counts))
        return
    await state.update_data(game_id=game.id, mode=GameMode.SOLO.value)
    await state.set_state(State.IN_GAME)
    await send_question(chat_id, game.id)


async def answer_callback(user_id: int, chat_id: int, payload: str) -> None:
    parts = payload.split(":")
    if len(parts) != 4:
        await send_text(chat_id, "Ответ устарел. Нажми /start")
        return
    game_id, position, selected = map(int, parts[1:])
    result = await db_manager.answer_game(game_id, user_id, position, selected, settings.GAME.answer_timeout)
    if not result.get("ok"):
        await send_text(chat_id, "Этот вопрос уже нельзя изменить. Нажми /start")
        return
    if result.get("duplicate"):
        await send_text(chat_id, "✅ Ответ уже засчитан.")
        return
    await _update_timer_message(game_id, position, "✅ Ответ принят")
    _cancel_question_timeout(game_id, position)
    _question_timer_messages.pop((game_id, position), None)
    game = result["game"]
    if result.get("game_over"):
        await finish_message(chat_id, game)
        return
    if result.get("timed_out"):
        feedback = f"⏰ Время вышло. Правильный ответ: {result['correct_answer']}"
    elif result["correct"]:
        feedback = "✅ Верно!"
    else:
        feedback = f"❌ Неверно. Правильный ответ: {result['correct_answer']}"
    await send_text(chat_id, feedback)
    await send_question(chat_id, game.id)


async def main() -> None:
    await init_db()
    if not settings.BOT.token:
        raise RuntimeError("BOT_TOKEN is required")
    try:
        if settings.BOT.mode == "webhook":
            raise RuntimeError("Webhook transport is configured separately; use BOT_MODE=polling for local beta")
        await bot.delete_webhook()
        await dp.start_polling(bot)
    finally:
        _cancel_all_question_timeouts()
        if http_client:
            await http_client.close()
        close_session = getattr(bot, "close_session", None)
        if close_session:
            await close_session()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
