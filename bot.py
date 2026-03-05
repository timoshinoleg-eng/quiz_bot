"""Основной файл бота MAX-Квиз."""
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
    logger.info("✅ maxapi installed successfully")
except ImportError as e:
    logger.warning(f"⚠️ maxapi not installed: {e}")
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

# Импорты проекта
try:
    from config import settings
    from db import init_db, close_db, db_manager
    from states import State, get_context, reset_state
    # Клавиатуры временно не используются из-за бага в maxapi 0.9.15
    from keyboards import get_main_menu_keyboard, get_topics_keyboard
    from questions import question_manager
    from models import QuestionCategory, DifficultyLevel, GameStatus
    PROJECT_IMPORTS_AVAILABLE = True
    logger.info("✅ All project imports successful")
except ImportError as e:
    logger.warning(f"⚠️ Project imports not available: {e}")
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

# Инициализация бота и диспетчера
if MAXAPI_AVAILABLE:
    bot = Bot()  # Автоматически читает MAX_BOT_TOKEN из env
    dp = Dispatcher()
else:
    bot = Bot(token=settings.BOT.token)
    dp = Dispatcher(bot)

logger.info(f"🤖 Bot initialized: {settings.BOT.token[:10] if settings.BOT.token else 'None'}...")

# ============ ОБРАБОТЧИКИ СОБЫТИЙ ============

@dp.bot_started()
async def handle_bot_started(event):
    """Обработка первого запуска бота."""
    logger.info("Bot started by user")
    if hasattr(event, 'bot') and hasattr(event, 'chat_id'):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text="🎯 Добро пожаловать в MAX-Квиз!\nОтправьте /start для начала игры."
        )

@dp.message_created(Command('start'))
async def cmd_start(event):
    """Обработчик команды /start."""
    logger.info("Command /start received")
    # ИСПРАВЛЕНО: используем sender.user_id и recipient.chat_id
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id  # или event.chat.id
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
        f"Играть в одиночном режиме\n"
        f"Получить Premium для эксклюзивных категорий\n\n"
        f"Выбери действие ниже:"
    )
    
    keyboard = get_main_menu_keyboard(is_premium)
    
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            attachments=[keyboard] if keyboard else None
        )
        logger.info("Message with keyboard sent successfully")
    except Exception as e:
        logger.error(f"Failed to send message with keyboard: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=welcome_text + "\n\n(Клавиатура недоступна - используйте /play)"
        )
    
    await db_manager.log_event("user_start", user_id)

@dp.message_created(Command('help'))
async def cmd_help(event):
    """Обработчик команды /help."""
    help_text = (
        "Помощь по MAX-Квиз\n\n"
        "Основные команды:\n"
        "/start - Главное меню\n"
        "/play - Начать игру\n"
        "/stats - Моя статистика\n"
        "/premium - Купить Premium\n\n"
        "Удачи!"
    )
    
    chat_id = event.message.chat.id
    await bot.send_message(chat_id=chat_id, text=help_text)

@dp.message_created(Command('play'))
async def cmd_play(event):
    """Обработчик команды /play."""
    await start_game_flow(event)

@dp.message_created(Command('stats'))
async def cmd_stats(event):
    """Обработчик команды /stats."""
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id
    user = await db_manager.get_or_create_user(user_id)
    
    games_played = getattr(user, 'games_played', 0)
    total_score = getattr(user, 'score_total', 0)
    daily_streak = getattr(user, 'daily_streak', 0)
    
    stats_text = (
        f"Твоя статистика\n\n"
        f"Игр сыграно: {games_played}\n"
        f"Общий счёт: {total_score}\n"
        f"Daily Streak: {daily_streak}"
    )
    
    await bot.send_message(chat_id=chat_id, text=stats_text)

@dp.message_callback()
async def handle_callback(event):
    """Обработчик callback-кнопок."""
    logger.info(f"Callback received: {getattr(event, 'payload', 'N/A')}")
    payload = getattr(event, 'payload', '')
    
    if hasattr(event, 'answer'):
        await event.answer()
    
    if payload.startswith("menu:"):
        await process_menu_callback(event, payload)
    elif payload.startswith("topic:"):
        await process_topic_callback(event, payload)
    elif payload.startswith("answer:"):
        await process_answer_callback(event, payload)

async def process_menu_callback(event, payload):
    """Обработка callback главного меню."""
    action = payload.split(":")[1] if ":" in payload else ""
    
    if action == "play":
        # ИСПРАВЛЕНО: используем sender.user_id и recipient.chat_id
        user_id = event.message.sender.user_id
        chat_id = event.message.recipient.chat_id
        state = await get_context(user_id)
        await state.set_state(State.SELECT_TOPIC)
        
        keyboard = get_topics_keyboard()
        text = "Выбери тему викторины:"
        await bot.send_message(chat_id=chat_id, text=text, attachments=[keyboard] if keyboard else None)

async def process_topic_callback(event, payload):
    """Обработка выбора темы."""
    topic = payload.split(":")[1] if ":" in payload else ""
    chat_id = event.message.recipient.chat_id
    
    if topic == "back":
        keyboard = get_main_menu_keyboard(False)
        await bot.send_message(chat_id=chat_id, text="Главное меню:", attachments=[keyboard] if keyboard else None)
        return
    
    user_id = event.message.sender.user_id
    state = await get_context(user_id)
    await state.update_data(selected_topic=topic)
    await state.set_state(State.SELECT_DIFFICULTY)
    
    # Показываем выбор сложности
    text = f"Тема: {topic}\n\nВыбери сложность:\n1. Легко\n2. Средне\n3. Сложно"
    await bot.send_message(chat_id=chat_id, text=text)

async def process_answer_callback(event, payload):
    """Обработка ответа на вопрос."""
    parts = payload.split(":") if ":" in payload else []
    
    if len(parts) < 4:
        if hasattr(event, 'answer'):
            await event.answer(text="⚠️ Ошибка: недействительный ответ")
        return
    
    is_correct = parts[3] == "True"
    result_text = "✅ Правильно!" if is_correct else "❌ Неправильно!"
    
    if hasattr(event, 'answer'):
        await event.answer(text=result_text, show_alert=False)

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def start_game_flow(event):
    """Запускает процесс начала игры."""
    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id
    state = await get_context(user_id)
    await state.set_state(State.SELECT_TOPIC)
    
    keyboard = get_topics_keyboard()
    text = "Выбери тему викторины:"
    await bot.send_message(chat_id=chat_id, text=text, attachments=[keyboard] if keyboard else None)

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
    await close_db()
    logger.info("✅ Bot stopped.")

async def main():
    """Главная функция запуска бота."""
    await on_startup()
    
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

# ИСПРАВЛЕНО: __name__ == "__main__" (с подчеркиваниями)
if __name__ == "__main__":
    asyncio.run(main())
