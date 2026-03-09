"""Основной файл бота MAX-Квиз с HTTP-клиентом для клавиатур."""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Загружаем переменные окружения из .env
from dotenv import load_dotenv
load_dotenv()

# Настройка логирования (ИСПРАВЛЕНО: для Windows)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)

# ИСПРАВЛЕНО: Устанавливаем кодировку для stdout в Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)

# Импорты maxapi (ИСПРАВЛЕНО: правильные типы для maxapi 0.9.15)
try:
    from maxapi import Bot, Dispatcher
    from maxapi.types import MessageCreated, MessageCallback, BotStarted, Command
    MAXAPI_AVAILABLE = True
    logger.info("maxapi installed successfully")
except ImportError as e:
    logger.warning(f"maxapi not installed: {e}")
    MAXAPI_AVAILABLE = False
    
    # Мок для разработки
    class MockBot:
        def __init__(self, token=None):
            self.token = token
            logger.info(f"MockBot initialized")
        
        async def send_message(self, chat_id, text, attachments=None, **kwargs):
            logger.info(f"[MOCK] send_message to {chat_id}: {text[:50]}...")
            print(f"\n[BOT] {text}\n")
        
        async def edit_message_text(self, chat_id, message_id, text, attachments=None, **kwargs):
            logger.info(f"[MOCK] edit_message_text: {text[:50]}...")
        
        async def answer_callback_query(self, callback_id, text=None, **kwargs):
            logger.info(f"[MOCK] answer_callback: {text}")
        
        async def delete_webhook(self):
            logger.info("[MOCK] delete_webhook")
    
    class MockDispatcher:
        def __init__(self, bot=None):
            self.bot = bot
        
        def bot_started(self):
            def decorator(f): return f
            return decorator
        
        def message_created(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        
        def message_callback(self):
            def decorator(f): return f
            return decorator
        
        async def start_polling(self, bot):
            logger.info("[MOCK] start_polling")
            while True:
                await asyncio.sleep(1)
    
    Bot = MockBot
    Dispatcher = MockDispatcher
    MessageCreated = type("MessageCreated", (), {})
    MessageCallback = type("MessageCallback", (), {})
    BotStarted = type("BotStarted", (), {})
    Command = lambda *args: lambda f: f

# Импорты HTTP-клиента и адаптера
try:
    from http_client import MaxHttpClient, HttpClientResponse
    from keyboard_adapter import KeyboardAdapter
    from keyboards_http import (
        get_main_menu_keyboard_http, get_topics_keyboard_http,
        get_stats_keyboard_http, get_premium_keyboard_http,
        get_difficulty_keyboard_http, get_question_count_keyboard_http,
        get_answers_keyboard_http, get_game_over_keyboard_http,
        get_feedback_keyboard_http
    )
    HTTP_CLIENT_AVAILABLE = True
    logger.info("HTTP client modules loaded")
except ImportError as e:
    logger.warning(f"HTTP client not available: {e}")
    HTTP_CLIENT_AVAILABLE = False

# Импорт форматтера отдельно (может быть недоступен если services не настроены)
try:
    from services.question_formatter import QuestionFormatter
    logger.info("QuestionFormatter loaded")
except ImportError as e:
    logger.warning(f"QuestionFormatter not available: {e}")
    QuestionFormatter = None

# Импорты проекта
try:
    from config import settings
    from db import init_db, close_db, db_manager
    from states import State, get_context, reset_state
    # Legacy keyboards (fallback)
    from keyboards import (
        get_main_menu_keyboard, get_topics_keyboard, get_stats_keyboard,
        get_premium_keyboard, get_difficulty_keyboard, get_question_count_keyboard,
        get_answers_keyboard, get_game_over_keyboard
    )
    from questions import question_manager
    from models import QuestionCategory, DifficultyLevel, GameStatus
    PROJECT_IMPORTS_AVAILABLE = True
    logger.info("All project imports successful")
except ImportError as e:
    logger.warning(f"Project imports not available: {e}")
    PROJECT_IMPORTS_AVAILABLE = False
    
    # Моки
    settings = type('Settings', (), {
        'BOT': type('BOT', (), {'token': os.getenv('MAX_BOT_TOKEN', '')})(),
        'PREMIUM': type('PREMIUM', (), {'price_rub': 299})()
    })()
    
    db_manager = type('DBManager', (), {
        'get_or_create_user': lambda **kwargs: type('User', (), {
            'games_played': 0, 'score_total': 0, 'games_won': 0,
            'daily_streak': 0, 'last_played': None
        })(),
        'is_premium': lambda **kwargs: False,
        'log_event': lambda **kwargs: None,
        'create_game': lambda **kwargs: type('Game', (), {
            'id': 1, 'status': 'in_progress'
        })(),
        'update_game_score': lambda **kwargs: None,
        'get_game': lambda **kwargs: type('Game', (), {
            'status': 'in_progress'
        })(),
        'complete_game': lambda **kwargs: None
    })()
    
    async def init_db():
        logger.info("[MOCK] Database initialized")
    
    async def close_db():
        logger.info("[MOCK] Database closed")
    
    async def get_context(user_id):
        return type('State', (), {
            'data': {},
            'set_state': lambda **kwargs: None,
            'update_data': lambda **kwargs: None,
            'get_data': lambda: {},
            'finish': lambda: None
        })()
    
    async def reset_state(user_id):
        pass
    
    State = type('State', (), {
        'SELECT_TOPIC': 'select_topic',
        'SELECT_DIFFICULTY': 'select_difficulty',
        'SELECT_QUESTION_COUNT': 'select_question_count',
        'IN_GAME': 'in_game'
    })()
    
    def get_main_menu_keyboard(**kwargs):
        return None
    
    def get_topics_keyboard():
        return None
    
    question_manager = type('QM', (), {
        'get_questions_for_game': lambda **kwargs: []
    })()
    
    QuestionCategory = type('QC', (), {
        'HISTORY': 'history', 'SCIENCE': 'science', 'SPORT': 'sport',
        'GEOGRAPHY': 'geography', 'ART': 'art', 'ENTERTAINMENT': 'entertainment'
    })()
    
    DifficultyLevel = type('DL', (), {
        'EASY': 'easy', 'MEDIUM': 'medium', 'HARD': 'hard'
    })()
    
    GameStatus = type('GS', (), {
        'IN_PROGRESS': 'in_progress', 'COMPLETED': 'completed', 'FAILED': 'failed'
    })()


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ДОСТУПА К ДАННЫМ ============

def get_user_id_from_event(event) -> int:
    """Извлекает user_id из события (MessageCreated или MessageCallback).
    
    Для MessageCreated: event.message.sender.user_id
    Для MessageCallback: event.callback.user.user_id
    """
    if hasattr(event, 'callback') and event.callback:
        # MessageCallback
        return event.callback.user.user_id
    elif hasattr(event, 'message') and event.message and event.message.sender:
        # MessageCreated
        return event.message.sender.user_id
    else:
        raise ValueError("Cannot extract user_id from event")


def get_chat_id_from_event(event) -> int:
    """Извлекает chat_id из события (MessageCreated или MessageCallback).
    
    Для MessageCreated: event.message.recipient.chat_id
    Для MessageCallback: event.chat.chat_id или event.message.recipient.chat_id
    """
    # Сначала пробуем получить из chat напрямую
    if hasattr(event, 'chat') and event.chat:
        return event.chat.chat_id
    # Затем из message.recipient
    elif hasattr(event, 'message') and event.message and event.message.recipient:
        return event.message.recipient.chat_id
    else:
        raise ValueError("Cannot extract chat_id from event")


def get_username_from_event(event) -> Optional[str]:
    """Извлекает username из события."""
    if hasattr(event, 'callback') and event.callback:
        return event.callback.user.username
    elif hasattr(event, 'message') and event.message and event.message.sender:
        return event.message.sender.username
    return None


def get_first_name_from_event(event) -> Optional[str]:
    """Извлекает first_name из события."""
    if hasattr(event, 'callback') and event.callback:
        return event.callback.user.first_name
    elif hasattr(event, 'message') and event.message and event.message.sender:
        return event.message.sender.first_name
    return None


# ============ ИНИЦИАЛИЗАЦИЯ БОТА ============

# Инициализация бота и диспетчера
if MAXAPI_AVAILABLE:
    bot = Bot()  # Автоматически читает MAX_BOT_TOKEN из env
    dp = Dispatcher()
else:
    bot = Bot(token=settings.BOT.token)
    dp = Dispatcher(bot)

logger.info(f"Bot initialized: {settings.BOT.token[:10] if settings.BOT.token else 'None'}...")

# Инициализация HTTP-клиента и адаптера клавиатур
http_client = None
keyboard_adapter = None

if HTTP_CLIENT_AVAILABLE and settings.BOT.token:
    http_client = MaxHttpClient(
        token=settings.BOT.token,
        timeout=30,
        max_retries=3
    )
    keyboard_adapter = KeyboardAdapter(
        bot=bot,
        http_client=http_client,
        prefer_http=True  # HTTP имеет приоритет (обход бага maxapi)
    )
    logger.info("HTTP client and keyboard adapter initialized")
else:
    logger.warning("HTTP client not initialized - falling back to maxapi only")

# Статистика ошибок для мониторинга
error_stats = {
    "total_messages": 0,
    "failed_messages": 0,
    "http_fallback_used": 0
}


# ============ ОБРАБОТЧИКИ СОБЫТИЙ ============

@dp.bot_started()
async def handle_bot_started(event):
    """Обработка первого запуска бота."""
    logger.info("Bot started by user")
    if hasattr(event, 'chat') and event.chat:
        chat_id = event.chat.chat_id
        await bot.send_message(
            chat_id=chat_id,
            text="🎯 Добро пожаловать в MAX-Квиз!\nОтправьте /start для начала игры."
        )


@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    """Обработчик команды /start."""
    logger.info("Command /start received")
    error_stats["total_messages"] += 1
    
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id
    username = event.message.sender.username
    first_name = event.message.sender.first_name
    
    user = await db_manager.get_or_create_user(
        user_id=user_id,
        username=username,
        first_name=first_name
    )
    
    await check_daily_streak(user_id)
    is_premium = await db_manager.is_premium(user_id)
    
    welcome_text = (
        f"Привет, {first_name or username or 'друг'}!\n\n"
        f"Добро пожаловать в MAX-Квиз!\n\n"
        f"Здесь ты можешь:\n"
        f"🎮 Играть в одиночном режиме\n"
        f"⭐ Получить Premium для эксклюзивных категорий\n\n"
        f"Выбери действие ниже:"
    )
    
    # Используем HTTP-адаптер для отправки с клавиатурой
    success = False
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        try:
            keyboard = get_main_menu_keyboard_http(is_premium)
            success = await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text=welcome_text,
                buttons=keyboard
            )
        except Exception as e:
            logger.error(f"HTTP adapter failed: {e}")
    
    # Fallback на стандартную отправку
    if not success:
        error_stats["http_fallback_used"] += 1
        try:
            keyboard = get_main_menu_keyboard(is_premium)
            await bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                attachments=[keyboard] if keyboard else None
            )
            success = True
        except Exception as e:
            logger.error(f"Fallback send failed: {e}")
    
    if not success:
        error_stats["failed_messages"] += 1
        await bot.send_message(
            chat_id=chat_id,
            text=welcome_text + "\n\n(Меню временно недоступно - используйте /play)"
        )
    
    await db_manager.log_event("user_start", user_id)


@dp.message_created(Command('help'))
async def cmd_help(event: MessageCreated):
    """Обработчик команды /help."""
    help_text = (
        "❓ Помощь по MAX-Квиз\n\n"
        "Основные команды:\n"
        "/start - Главное меню\n"
        "/play - Начать игру\n"
        "/stats - Моя статистика\n"
        "/premium - Купить Premium\n\n"
        "Удачи! 🍀"
    )
    
    chat_id = event.message.recipient.chat_id
    await bot.send_message(chat_id=chat_id, text=help_text)


@dp.message_created(Command('play'))
async def cmd_play(event: MessageCreated):
    """Обработчик команды /play."""
    await start_game_flow(event)


@dp.message_created(Command('stats'))
async def cmd_stats(event: MessageCreated):
    """Обработчик команды /stats с улучшенным форматированием."""
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id
    user = await db_manager.get_or_create_user(user_id)
    
    games_played = getattr(user, 'games_played', 0)
    total_score = getattr(user, 'score_total', 0)
    daily_streak = getattr(user, 'daily_streak', 0)
    
    # Используем улучшенный форматтер если доступен
    if QuestionFormatter is not None:
        stats_text = QuestionFormatter.format_stats_text(
            total_games=games_played,
            total_answers=total_score,  # Предполагаем, что total_score ~ количество ответов
            correct_answers=getattr(user, 'correct_answers', total_score // 2),
            best_category=getattr(user, 'best_category', None)
        )
    else:
        stats_text = (
            f"📊 Твоя статистика\n\n"
            f"🎮 Игр сыграно: {games_played}\n"
            f"🏆 Общий счёт: {total_score}\n"
            f"🔥 Daily Streak: {daily_streak}"
        )
    
    # Отправка через HTTP-адаптер
    success = False
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        try:
            keyboard = get_stats_keyboard_http()
            success = await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text=stats_text,
                buttons=keyboard
            )
        except Exception as e:
            logger.error(f"HTTP adapter failed: {e}")
    
    if not success:
        try:
            keyboard = get_stats_keyboard()
            await bot.send_message(
                chat_id=chat_id,
                text=stats_text,
                attachments=[keyboard] if keyboard else None
            )
        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=stats_text)


@dp.message_created(Command('premium'))
async def cmd_premium(event: MessageCreated):
    """Обработчик команды /premium."""
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id
    
    premium_text = (
        f"⭐ MAX-Квиз Premium\n\n"
        f"Получи доступ к эксклюзивным категориям:\n"
        f"• Искусство\n"
        f"• Развлечения\n"
        f"• Специальные вопросы\n\n"
        f"Цена: {settings.PREMIUM.price_rub} руб./мес"
    )
    
    # Отправка через HTTP-адаптер
    success = False
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        try:
            keyboard = get_premium_keyboard_http()
            success = await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text=premium_text,
                buttons=keyboard
            )
        except Exception as e:
            logger.error(f"HTTP adapter failed: {e}")
    
    if not success:
        try:
            keyboard = get_premium_keyboard()
            await bot.send_message(
                chat_id=chat_id,
                text=premium_text,
                attachments=[keyboard] if keyboard else None
            )
        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=premium_text)


@dp.message_callback()
async def handle_callback(event: MessageCallback):
    """Обработчик callback-кнопок."""
    payload = event.callback.payload if event.callback else ""
    logger.info(f"Callback received: {payload}")
    
    # Отвечаем на callback через HTTP-клиент (обязательно в течение 10 сек!)
    if http_client and event.callback:
        try:
            response = await http_client.answer_callback_query(
                callback_id=event.callback.callback_id,
                text=None,  # или "Принято!" если нужно показать уведомление
                show_alert=False
            )
            if not response.success:
                logger.warning(f"Failed to answer callback: {response.error_message}")
        except Exception as e:
            logger.error(f"Error answering callback: {e}")
    elif hasattr(event, 'answer'):
        # Fallback на встроенный метод
        try:
            await event.answer()
        except Exception as e:
            logger.warning(f"Failed to answer callback via event: {e}")
    
    # Обработка payload
    if payload.startswith("menu:"):
        await process_menu_callback(event, payload)
    elif payload.startswith("topic:"):
        await process_topic_callback(event, payload)
    elif payload.startswith("difficulty:"):
        await process_difficulty_callback(event, payload)
    elif payload.startswith("count:"):
        await process_count_callback(event, payload)
    elif payload.startswith("answer:"):
        await process_answer_callback(event, payload)
    elif payload.startswith("game:"):
        await process_game_callback(event, payload)
    elif payload.startswith("premium:"):
        await process_premium_callback(event, payload)


async def process_menu_callback(event: MessageCallback, payload: str):
    """Обработка callback главного меню."""
    action = payload.split(":")[1] if ":" in payload else ""
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    
    if action == "play":
        await start_game_flow(event)
    
    elif action == "stats":
        user = await db_manager.get_or_create_user(user_id)
        games_played = getattr(user, 'games_played', 0)
        total_score = getattr(user, 'score_total', 0)
        daily_streak = getattr(user, 'daily_streak', 0)
        
        if QuestionFormatter is not None:
            stats_text = QuestionFormatter.format_stats_text(
                total_games=games_played,
                total_answers=total_score,
                correct_answers=getattr(user, 'correct_answers', total_score // 2),
                best_category=getattr(user, 'best_category', None)
            )
        else:
            stats_text = (
                f"📊 Твоя статистика\n\n"
                f"🎮 Игр сыграно: {games_played}\n"
                f"🏆 Общий счёт: {total_score}\n"
                f"🔥 Daily Streak: {daily_streak}"
            )
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_stats_keyboard_http()
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text=stats_text,
                buttons=keyboard
            )
        else:
            await bot.send_message(chat_id=chat_id, text=stats_text)
    
    elif action == "premium":
        premium_text = (
            f"⭐ MAX-Квиз Premium\n\n"
            f"Получи доступ к эксклюзивным категориям!\n\n"
            f"Цена: {settings.PREMIUM.price_rub} руб./мес"
        )
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_premium_keyboard_http()
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text=premium_text,
                buttons=keyboard
            )
        else:
            await bot.send_message(chat_id=chat_id, text=premium_text)
    
    elif action == "help":
        help_text = (
            "❓ Помощь по MAX-Квиз\n\n"
            "Основные команды:\n"
            "/start - Главное меню\n"
            "/play - Начать игру\n"
            "/stats - Моя статистика\n"
            "/premium - Купить Premium\n\n"
            "Удачи! 🍀"
        )
        await bot.send_message(chat_id=chat_id, text=help_text)
    
    elif action == "back":
        is_premium = await db_manager.is_premium(user_id)
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_main_menu_keyboard_http(is_premium)
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text="🏠 Главное меню:",
                buttons=keyboard
            )
        else:
            keyboard = get_main_menu_keyboard(is_premium)
            await bot.send_message(
                chat_id=chat_id,
                text="🏠 Главное меню:",
                attachments=[keyboard] if keyboard else None
            )


async def process_topic_callback(event: MessageCallback, payload: str):
    """Обработка выбора темы."""
    topic = payload.split(":")[1] if ":" in payload else ""
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    
    if topic == "back":
        is_premium = await db_manager.is_premium(user_id)
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_main_menu_keyboard_http(is_premium)
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text="🏠 Главное меню:",
                buttons=keyboard
            )
        else:
            keyboard = get_main_menu_keyboard(is_premium)
            await bot.send_message(
                chat_id=chat_id,
                text="🏠 Главное меню:",
                attachments=[keyboard] if keyboard else None
            )
        return
    
    # Сохраняем выбранную тему
    state = await get_context(user_id)
    await state.update_data(selected_topic=topic)
    await state.set_state(State.SELECT_DIFFICULTY)
    
    # Показываем выбор сложности с улучшенным форматированием
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        keyboard = get_difficulty_keyboard_http()
        if QuestionFormatter is not None:
            text = QuestionFormatter.format_difficulty_selection_text()
        else:
            text = f"🎯 Тема: {topic}\n\nВыбери сложность:"
        await keyboard_adapter.send_with_keyboard(
            chat_id=chat_id,
            text=text,
            buttons=keyboard
        )
    else:
        text = f"🎯 Тема: {topic}\n\nВыбери сложность:\n1. Легко\n2. Средне\n3. Сложно"
        await bot.send_message(chat_id=chat_id, text=text)


async def process_difficulty_callback(event: MessageCallback, payload: str):
    """Обработка выбора сложности."""
    difficulty = payload.split(":")[1] if ":" in payload else ""
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    
    if difficulty == "back":
        state = await get_context(user_id)
        await state.set_state(State.SELECT_TOPIC)
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_topics_keyboard_http()
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text="🎯 Выбери тему викторины:",
                buttons=keyboard
            )
        else:
            keyboard = get_topics_keyboard()
            await bot.send_message(
                chat_id=chat_id,
                text="🎯 Выбери тему викторины:",
                attachments=[keyboard] if keyboard else None
            )
        return
    
    # Сохраняем выбранную сложность
    state = await get_context(user_id)
    await state.update_data(selected_difficulty=difficulty)
    await state.set_state(State.SELECT_QUESTION_COUNT)
    
    # Показываем выбор количества вопросов
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        keyboard = get_question_count_keyboard_http()
        if QuestionFormatter is not None:
            text = QuestionFormatter.format_question_count_text()
        else:
            difficulty_names = {
                'easy': '🟢 Легко',
                'medium': '🟡 Средне', 
                'hard': '🔴 Сложно'
            }
            text = f"⚙️ Сложность: {difficulty_names.get(difficulty, difficulty)}\n\nВыбери количество вопросов:"
        await keyboard_adapter.send_with_keyboard(
            chat_id=chat_id,
            text=text,
            buttons=keyboard
        )
    else:
        text = f"Тема сохранена. Выбери количество вопросов (5, 10, 15, 20):"
        await bot.send_message(chat_id=chat_id, text=text)


async def process_count_callback(event: MessageCallback, payload: str):
    """Обработка выбора количества вопросов."""
    count_str = payload.split(":")[1] if ":" in payload else ""
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    
    if count_str == "back":
        state = await get_context(user_id)
        await state.set_state(State.SELECT_DIFFICULTY)
        
        if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
            keyboard = get_difficulty_keyboard_http()
            await keyboard_adapter.send_with_keyboard(
                chat_id=chat_id,
                text="Выбери сложность:",
                buttons=keyboard
            )
        else:
            await bot.send_message(chat_id=chat_id, text="Выбери сложность:")
        return
    
    try:
        question_count = int(count_str)
    except ValueError:
        question_count = 10
    
    # Запускаем игру
    state = await get_context(user_id)
    data = await state.get_data()
    topic = data.get('selected_topic', 'general')
    difficulty = data.get('selected_difficulty', 'medium')
    
    # Создаем игру в БД
    game = await db_manager.create_game(
        user_id=user_id,
        category=topic,
        difficulty=difficulty,
        question_count=question_count
    )
    
    await state.update_data(
        game_id=game.id,
        current_question=0,
        score=0
    )
    await state.set_state(State.IN_GAME)
    
    # Отправляем первый вопрос
    await send_question(chat_id, user_id, game.id, 0)


async def send_question(chat_id: int, user_id: int, game_id: int, question_index: int):
    """Отправляет вопрос игроку с улучшенным форматированием."""
    state = await get_context(user_id)
    data = await state.get_data()
    topic = data.get('selected_topic', 'general')
    difficulty = data.get('selected_difficulty', 'medium')
    
    questions = await question_manager.get_questions_for_game(
        category=topic,
        difficulty=difficulty,
        count=data.get('question_count', 10)
    )
    
    if question_index >= len(questions):
        await finish_game(chat_id, user_id, game_id)
        return
    
    question = questions[question_index]
    
    # Используем улучшенный форматтер
    if QuestionFormatter is not None:
        question_text = QuestionFormatter.format_question_text(
            question_text=question.text,
            question_number=question_index + 1,
            total_questions=len(questions),
            category=question.category,
            difficulty=question.difficulty
        )
    else:
        # Fallback для совместимости
        question_text = (
            f"❓ Вопрос {question_index + 1}/{len(questions)}\n\n"
            f"{question.text}"
        )
    
    # Создаем клавиатуру с ответами
    all_answers = [question.correct_answer] + question.wrong_answers
    import random
    random.shuffle(all_answers)
    correct_index = all_answers.index(question.correct_answer)
    
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        keyboard = get_answers_keyboard_http(
            all_answers, question_index, game_id, correct_index,
            total_questions=len(questions)
        )
        await keyboard_adapter.send_with_keyboard(
            chat_id=chat_id,
            text=question_text,
            buttons=keyboard
        )
    else:
        await bot.send_message(chat_id=chat_id, text=question_text)


async def finish_game(chat_id: int, user_id: int, game_id: int):
    """Завершает игру и показывает улучшенные результаты."""
    state = await get_context(user_id)
    data = await state.get_data()
    score = data.get('score', 0)
    total = data.get('current_question', 0)
    topic = data.get('selected_topic', 'general')
    difficulty = data.get('selected_difficulty', 'medium')
    
    await db_manager.complete_game(game_id, score=score, correct_answers=score)
    
    # Используем улучшенный форматтер
    if QuestionFormatter is not None:
        result_text = QuestionFormatter.format_result_text(
            score=score,
            total=total,
            category=topic,
            difficulty=difficulty
        )
    else:
        # Fallback для совместимости
        result_text = (
            f"🎮 Игра окончена!\n\n"
            f"🏆 Счёт: {score}/{total}\n"
            f"📊 Процент: {score/max(total, 1)*100:.1f}%"
        )
    
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        keyboard = get_game_over_keyboard_http(game_id, score, total)
        await keyboard_adapter.send_with_keyboard(
            chat_id=chat_id,
            text=result_text,
            buttons=keyboard
        )
    else:
        await bot.send_message(chat_id=chat_id, text=result_text)
    
    await state.finish()


async def process_answer_callback(event: MessageCallback, payload: str):
    """Обработка ответа на вопрос."""
    parts = payload.split(":") if ":" in payload else []
    
    if len(parts) < 5:
        if http_client and event.callback:
            await http_client.answer_callback_query(
                callback_id=event.callback.callback_id,
                text="⚠️ Ошибка: недействительный ответ",
                show_alert=True
            )
        return
    
    try:
        game_id = int(parts[1])
        question_index = int(parts[2])
        selected_index = int(parts[3])
        correct_index = int(parts[4])
    except (ValueError, IndexError):
        return
    
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    
    is_correct = selected_index == correct_index
    result_text = "✅ Правильно!" if is_correct else "❌ Неправильно!"
    
    # Отвечаем на callback
    if http_client and event.callback:
        try:
            await http_client.answer_callback_query(
                callback_id=event.callback.callback_id,
                text=result_text,
                show_alert=True
            )
        except Exception as e:
            logger.warning(f"Failed to answer callback: {e}")
    
    # Обновляем счет
    state = await get_context(user_id)
    data = await state.get_data()
    current_score = data.get('score', 0)
    
    if is_correct:
        current_score += 1
        await state.update_data(score=current_score)
    
    await state.update_data(current_question=question_index + 1)
    
    # Отправляем следующий вопрос
    await send_question(chat_id, user_id, game_id, question_index + 1)


async def process_game_callback(event: MessageCallback, payload: str):
    """Обработка callback игры (рестарт и т.д.)."""
    action = payload.split(":")[1] if ":" in payload else ""
    
    if action == "restart":
        await start_game_flow(event)


async def process_premium_callback(event: MessageCallback, payload: str):
    """Обработка callback Premium."""
    action = payload.split(":")[1] if ":" in payload else ""
    chat_id = get_chat_id_from_event(event)
    
    if action == "buy":
        await bot.send_message(
            chat_id=chat_id,
            text="💳 Функция оплаты в разработке.\nОбратитесь к администратору."
        )


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def start_game_flow(event):
    """Запускает процесс начала игры."""
    user_id = get_user_id_from_event(event)
    chat_id = get_chat_id_from_event(event)
    state = await get_context(user_id)
    await state.set_state(State.SELECT_TOPIC)
    
    if keyboard_adapter and HTTP_CLIENT_AVAILABLE:
        keyboard = get_topics_keyboard_http()
        if QuestionFormatter is not None:
            text = QuestionFormatter.format_category_selection_text()
        else:
            text = "🎯 Выбери тему викторины:"
        await keyboard_adapter.send_with_keyboard(
            chat_id=chat_id,
            text=text,
            buttons=keyboard
        )
    else:
        keyboard = get_topics_keyboard()
        text = "🎯 Выбери тему викторины:"
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            attachments=[keyboard] if keyboard else None
        )


async def check_daily_streak(user_id):
    """Проверяет и обновляет daily streak пользователя."""
    user = await db_manager.get_or_create_user(user_id)
    
    if getattr(user, 'last_played', None):
        days_since_last = (datetime.utcnow() - user.last_played).days
        
        if days_since_last == 1:
            user.daily_streak += 1
        elif days_since_last > 1:
            user.daily_streak = 1
    else:
        user.daily_streak = 1
    
    user.last_played = datetime.utcnow()


# ============ ЗАПУСК БОТА ============

async def on_startup():
    """Действия при запуске бота."""
    logger.info("🚀 Starting MAX-Квиз bot...")
    await init_db()
    
    if MAXAPI_AVAILABLE and hasattr(bot, 'get_me'):
        try:
            me = await bot.get_me()
            logger.info(f"✅ Bot authenticated: {getattr(me, 'username', 'N/A')}")
        except Exception as e:
            logger.error(f"❌ Token verification failed: {e}")
    
    logger.info("✅ Bot started successfully!")


async def on_shutdown():
    """Действия при остановке бота."""
    logger.info("🛑 Shutting down bot...")
    
    # Закрываем HTTP-сессию
    if http_client:
        await http_client.close()
        logger.info("HTTP client closed")
    
    await close_db()
    logger.info("✅ Bot stopped.")


async def print_error_stats():
    """Периодический вывод статистики ошибок."""
    while True:
        await asyncio.sleep(300)  # Каждые 5 минут
        logger.info(
            f"Error stats: total={error_stats['total_messages']}, "
            f"failed={error_stats['failed_messages']}, "
            f"http_fallback={error_stats['http_fallback_used']}"
        )


async def main():
    """Главная функция запуска бота."""
    await on_startup()
    
    # Запуск фоновой задачи статистики
    asyncio.create_task(print_error_stats())
    
    try:
        if MAXAPI_AVAILABLE and PROJECT_IMPORTS_AVAILABLE:
            await bot.delete_webhook()
            logger.info("🔄 Starting Long Polling mode...")
            await dp.start_polling(bot)
        else:
            logger.info("🧪 Running in MOCK mode...")
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("⌨️ Bot stopped by user")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
