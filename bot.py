"""Основной файл бота MAX-Квиз.

Этот модуль содержит:
- Инициализацию диспетчера maxapi
- Все хендлеры команд и callback
- Главный цикл бота

Example:
    >>> python bot.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Импорты maxapi
try:
    from maxapi import Bot, Dispatcher
    from maxapi.types import Message, CallbackQuery
    from maxapi.filters import Command
except ImportError:
    logger.error("maxapi not installed. Using mock for development.")
    # Мок для разработки
    class MockBot:
        async def send_message(self, *args, **kwargs): pass
        async def edit_message_text(self, *args, **kwargs): pass
        async def answer_callback_query(self, *args, **kwargs): pass
        async def delete_message(self, *args, **kwargs): pass
    
    class MockDispatcher:
        def message_handler(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def callback_query_handler(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
    
    Bot = MockBot
    Dispatcher = MockDispatcher
    Message = type("Message", (), {"from_user": type("User", (), {"id": 1, "username": "test"})()})
    CallbackQuery = type("CallbackQuery", (), {"from_user": type("User", (), {"id": 1})(), "data": "", "id": "1"})()
    Command = lambda x: x

from config import settings
from db import init_db, close_db, db_manager
from states import (
    State, get_context, reset_state, state_filter,
    GameStates
)
from keyboards import (
    get_main_menu_keyboard, get_topics_keyboard, get_difficulty_keyboard,
    get_question_count_keyboard, get_answers_keyboard, get_game_over_keyboard,
    get_duel_menu_keyboard, get_premium_keyboard, get_stats_keyboard,
    format_category, format_difficulty, remove_keyboard
)
from questions import question_manager, QuestionLoader
from models import QuestionCategory, DifficultyLevel, GameStatus


# Инициализация бота и диспетчера
bot = Bot(token=settings.BOT.token)
dp = Dispatcher(bot)


# ============ КОМАНДЫ ============

@dp.message_handler(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start.
    
    Args:
        message: Сообщение от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Создаём или получаем пользователя
    user = await db_manager.get_or_create_user(
        user_id=user_id,
        username=username,
        first_name=first_name
    )
    
    # Проверяем daily streak
    await check_daily_streak(user_id)
    
    is_premium = await db_manager.is_premium(user_id)
    
    welcome_text = (
        f"👋 Привет, {first_name or username or 'друг'}!\n\n"
        f"🎯 Добро пожаловать в <b>MAX-Квиз</b>!\n\n"
        f"Здесь ты можешь:\n"
        f"🎮 Играть в одиночном режиме\n"
        f"⚔️ Соревноваться с друзьями в дуэлях\n"
        f"⭐ Получить Premium для эксклюзивных категорий\n\n"
        f"Выбери действие ниже 👇"
    )
    
    await message.reply(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_premium),
        parse_mode="HTML"
    )
    
    # Логируем событие
    await db_manager.log_event("user_start", user_id)


@dp.message_handler(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help.
    
    Args:
        message: Сообщение от пользователя
    """
    help_text = (
        "📖 <b>Помощь по MAX-Квиз</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Главное меню\n"
        "/play - Начать игру\n"
        "/duel - Создать дуэль\n"
        "/stats - Моя статистика\n"
        "/premium - Купить Premium\n\n"
        "<b>Как играть:</b>\n"
        "1. Выбери тему (История, Наука, Спорт...)\n"
        "2. Выбери сложность (Легко, Средне, Сложно)\n"
        "3. Выбери количество вопросов (5, 10, 15)\n"
        "4. Отвечай на вопросы за 30 секунд\n"
        "5. Получай очки за правильные ответы и скорость!\n\n"
        "<b>Жизни:</b> У тебя 3 жизни. За каждую ошибку теряешь одну. "
        "Когда жизни закончатся - игра окончена.\n\n"
        "<b>Очки:</b>\n"
        "• Правильный ответ: +100 очков\n"
        "• Бонус за скорость: до +50 очков\n\n"
        "Удачи! 🍀"
    )
    
    await message.reply(help_text, parse_mode="HTML")


@dp.message_handler(Command("play"))
async def cmd_play(message: Message) -> None:
    """Обработчик команды /play - начало игры.
    
    Args:
        message: Сообщение от пользователя
    """
    await start_game_flow(message)


@dp.message_handler(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Обработчик команды /stats - статистика.
    
    Args:
        message: Сообщение от пользователя
    """
    user_id = message.from_user.id
    user = await db_manager.get_or_create_user(user_id)
    
    # Получаем статистику
    games_played = user.games_played
    total_score = user.score_total
    games_won = user.games_won
    win_rate = (games_won / games_played * 100) if games_played > 0 else 0
    daily_streak = user.daily_streak
    
    stats_text = (
        f"📊 <b>Твоя статистика</b>\n\n"
        f"🎮 Игр сыграно: <b>{games_played}</b>\n"
        f"🏆 Побед: <b>{games_won}</b>\n"
        f"📈 Процент побед: <b>{win_rate:.1f}%</b>\n"
        f"⭐ Общий счёт: <b>{total_score}</b>\n"
        f"🔥 Daily Streak: <b>{daily_streak}</b>\n\n"
        f"Продолжай играть, чтобы улучшить свои результаты!"
    )
    
    await message.reply(stats_text, reply_markup=get_stats_keyboard())


@dp.message_handler(Command("premium"))
async def cmd_premium(message: Message) -> None:
    """Обработчик команды /premium - информация о Premium.
    
    Args:
        message: Сообщение от пользователя
    """
    premium_text = (
        f"⭐ <b>MAX-Квиз Premium</b>\n\n"
        f"<b>Цена:</b> {settings.PREMIUM.price_rub}₽/месяц\n\n"
        f"<b>Включено:</b>\n"
        f"✅ Игра без рекламы\n"
        f"✅ Доступ к эксклюзивным категориям\n"
        f"✅ Неограниченные подсказки\n"
        f"✅ Удвоенные очки за игры\n"
        f"✅ Эксклюзивные достижения\n"
        f"✅ Приоритетная поддержка\n\n"
        f"Оформи Premium прямо сейчас!"
    )
    
    await message.reply(premium_text, reply_markup=get_premium_keyboard())


# ============ CALLBACK ХЕНДЛЕРЫ ============

@dp.callback_query_handler(lambda c: c.data.startswith("menu:"))
async def process_menu_callback(callback: CallbackQuery) -> None:
    """Обработчик callback главного меню.
    
    Args:
        callback: Callback запрос
    """
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if action == "play":
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Выбери тему викторины:",
            reply_markup=get_topics_keyboard()
        )
        
        # Устанавливаем состояние
        state = await get_context(user_id)
        await state.set_state(State.SELECT_TOPIC)
        
    elif action == "duel":
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="⚔️ <b>Режим дуэли</b>\n\n"
                 "Создай дуэль и пригласи друга или присоединись к существующей!",
            reply_markup=get_duel_menu_keyboard(),
            parse_mode="HTML"
        )
        
    elif action == "stats":
        await cmd_stats(callback.message)
        
    elif action == "premium":
        await cmd_premium(callback.message)
        
    elif action == "help":
        await cmd_help(callback.message)
    
    await bot.answer_callback_query(callback.id)


@dp.callback_query_handler(lambda c: c.data.startswith("topic:"))
async def process_topic_callback(callback: CallbackQuery) -> None:
    """Обработчик выбора темы.
    
    Args:
        callback: Callback запрос
    """
    topic = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if topic == "back":
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Главное меню:",
            reply_markup=get_main_menu_keyboard(await db_manager.is_premium(user_id))
        )
        await reset_state(user_id)
        await bot.answer_callback_query(callback.id)
        return
    
    # Сохраняем выбранную тему
    state = await get_context(user_id)
    await state.update_data(selected_topic=topic)
    await state.set_state(State.SELECT_DIFFICULTY)
    
    topic_name = format_category(QuestionCategory(topic))
    
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"Тема: {topic_name}\n\nТеперь выбери сложность:",
        reply_markup=get_difficulty_keyboard()
    )
    
    await bot.answer_callback_query(callback.id)


@dp.callback_query_handler(lambda c: c.data.startswith("diff:"))
async def process_difficulty_callback(callback: CallbackQuery) -> None:
    """Обработчик выбора сложности.
    
    Args:
        callback: Callback запрос
    """
    difficulty = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if difficulty == "back":
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Выбери тему викторины:",
            reply_markup=get_topics_keyboard()
        )
        state = await get_context(user_id)
        await state.set_state(State.SELECT_TOPIC)
        await bot.answer_callback_query(callback.id)
        return
    
    # Сохраняем сложность
    state = await get_context(user_id)
    await state.update_data(selected_difficulty=difficulty)
    await state.set_state(State.SELECT_QUESTION_COUNT)
    
    difficulty_name = format_difficulty(DifficultyLevel(difficulty))
    
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"Сложность: {difficulty_name}\n\nСколько вопросов?",
        reply_markup=get_question_count_keyboard()
    )
    
    await bot.answer_callback_query(callback.id)


@dp.callback_query_handler(lambda c: c.data.startswith("count:"))
async def process_count_callback(callback: CallbackQuery) -> None:
    """Обработчик выбора количества вопросов.
    
    Args:
        callback: Callback запрос
    """
    count_str = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    if count_str == "back":
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Выбери сложность:",
            reply_markup=get_difficulty_keyboard()
        )
        state = await get_context(user_id)
        await state.set_state(State.SELECT_DIFFICULTY)
        await bot.answer_callback_query(callback.id)
        return
    
    count = int(count_str)
    
    # Получаем данные из состояния
    state = await get_context(user_id)
    state_data = await state.get_data()
    
    topic = state_data.get("selected_topic")
    difficulty = state_data.get("selected_difficulty")
    
    # Создаём игру
    game = await db_manager.create_game(
        user_id=user_id,
        category=QuestionCategory(topic),
        difficulty=DifficultyLevel(difficulty),
        question_count=count
    )
    
    # Получаем вопросы
    questions = await question_manager.get_questions_for_game(
        category=QuestionCategory(topic),
        difficulty=DifficultyLevel(difficulty),
        count=count
    )
    
    if not questions:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="😔 К сожалению, вопросы по этой теме временно недоступны.\n"
                 "Попробуй выбрать другую тему!",
            reply_markup=get_topics_keyboard()
        )
        await bot.answer_callback_query(callback.id)
        return
    
    # Сохраняем вопросы в состоянии
    question_ids = [q.id for q in questions]
    await state.update_data(
        game_id=game.id,
        questions=question_ids,
        current_question=0,
        score=0,
        lives=3
    )
    await state.set_state(State.IN_GAME)
    
    # Показываем первый вопрос
    await send_question(callback.message.chat.id, game.id, questions[0], 0, count)
    
    await bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    await bot.answer_callback_query(callback.id)


@dp.callback_query_handler(lambda c: c.data.startswith("answer:"))
async def process_answer_callback(callback: CallbackQuery) -> None:
    """Обработчик ответа на вопрос.
    
    Args:
        callback: Callback запрос
    """
    parts = callback.data.split(":")
    game_id = int(parts[1])
    question_index = int(parts[2])
    answer_index = int(parts[3])
    is_correct = parts[4] == "True"
    
    user_id = callback.from_user.id
    
    # Обновляем счёт
    points = 100 if is_correct else 0
    if is_correct:
        # Бонус за скорость можно добавить здесь
        pass
    
    await db_manager.update_game_score(game_id, points, is_correct)
    
    # Получаем состояние
    state = await get_context(user_id)
    state_data = await state.get_data()
    
    current = state_data.get("current_question", 0) + 1
    questions = state_data.get("questions", [])
    total = len(questions)
    lives = state_data.get("lives", 3) - (0 if is_correct else 1)
    score = state_data.get("score", 0) + points
    
    await state.update_data(current_question=current, lives=lives, score=score)
    
    # Показываем результат
    if is_correct:
        result_text = f"✅ Правильно! +{points} очков"
    else:
        result_text = f"❌ Неправильно! Осталось жизней: {lives}"
    
    await bot.answer_callback_query(callback.id, text=result_text, show_alert=False)
    
    # Проверяем конец игры
    game = await db_manager.get_game(game_id)
    
    if lives <= 0 or current >= total or game.status != GameStatus.IN_PROGRESS:
        # Игра окончена
        await finish_game(callback.message.chat.id, game_id, score, current, total)
        await state.finish()
    else:
        # Следующий вопрос
        from db import get_db
        from sqlalchemy import select
        from models import Question
        
        async with get_db() as db:
            result = await db.execute(
                select(Question).where(Question.id == questions[current])
            )
            next_question = result.scalar_one()
        
        await send_question(
            callback.message.chat.id,
            game_id,
            next_question,
            current,
            total
        )


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def start_game_flow(message: Message) -> None:
    """Запускает процесс начала игры.
    
    Args:
        message: Сообщение от пользователя
    """
    user_id = message.from_user.id
    
    state = await get_context(user_id)
    await state.set_state(State.SELECT_TOPIC)
    
    await message.reply(
        "Выбери тему викторины:",
        reply_markup=get_topics_keyboard()
    )


async def send_question(
    chat_id: int,
    game_id: int,
    question,
    current_index: int,
    total: int
) -> None:
    """Отправляет вопрос пользователю.
    
    Args:
        chat_id: ID чата
        game_id: ID игры
        question: Объект вопроса
        current_index: Номер текущего вопроса
        total: Общее количество вопросов
    """
    # Перемешиваем ответы
    answers = question_manager.shuffle_answers(question)
    
    question_text = (
        f"Вопрос {current_index + 1}/{total}\n\n"
        f"{question.text}"
    )
    
    await bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=get_answers_keyboard(answers, current_index, game_id)
    )


async def finish_game(
    chat_id: int,
    game_id: int,
    score: int,
    answered: int,
    total: int
) -> None:
    """Завершает игру и показывает результаты.
    
    Args:
        chat_id: ID чата
        game_id: ID игры
        score: Набранные очки
        answered: Количество отвеченных вопросов
        total: Общее количество вопросов
    """
    await db_manager.complete_game(game_id)
    
    # Определяем оценку
    if score >= total * 130:
        rating = "🏆 Отлично!"
    elif score >= total * 100:
        rating = "⭐ Хорошо!"
    elif score >= total * 70:
        rating = "👍 Неплохо!"
    else:
        rating = "💪 Попробуй ещё!"
    
    result_text = (
        f"🎮 <b>Игра окончена!</b>\n\n"
        f"{rating}\n\n"
        f"📊 Результат: <b>{answered}/{total}</b> вопросов\n"
        f"⭐ Очков набрано: <b>{score}</b>\n\n"
        f"Спасибо за игру!"
    )
    
    await bot.send_message(
        chat_id=chat_id,
        text=result_text,
        reply_markup=get_game_over_keyboard(game_id),
        parse_mode="HTML"
    )


async def check_daily_streak(user_id: int) -> None:
    """Проверяет и обновляет daily streak пользователя.
    
    Args:
        user_id: ID пользователя
    """
    user = await db_manager.get_or_create_user(user_id)
    
    from datetime import datetime, timedelta
    
    if user.last_played:
        days_since_last = (datetime.utcnow() - user.last_played).days
        
        if days_since_last == 1:
            # Продолжаем streak
            user.daily_streak += 1
            # Можно отправить уведомление о награде
        elif days_since_last > 1:
            # Сбрасываем streak
            user.daily_streak = 1
    else:
        user.daily_streak = 1
    
    user.last_played = datetime.utcnow()


# ============ ЗАПУСК БОТА ============

async def on_startup() -> None:
    """Действия при запуске бота."""
    logger.info("Starting MAX-Квиз bot...")
    await init_db()
    logger.info("Bot started successfully!")


async def on_shutdown() -> None:
    """Действия при остановке бота."""
    logger.info("Shutting down bot...")
    await close_db()
    logger.info("Bot stopped.")


async def main() -> None:
    """Главная функция запуска бота."""
    await on_startup()
    
    try:
        # Запуск polling
        # await dp.start_polling()
        logger.info("Bot is running...")
        
        # Для разработки - просто держим бота запущенным
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
