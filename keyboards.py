"""Inline-клавиатуры для MAX-Квиз (используем InlineKeyboardBuilder)."""
import logging
from typing import Optional

# ИСПРАВЛЕНО: используем InlineKeyboardBuilder и CallbackButton
try:
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    from maxapi.types import CallbackButton
    MAXAPI_TYPES_AVAILABLE = True
except ImportError as e:
    MAXAPI_TYPES_AVAILABLE = False
    logging.warning(f"maxapi types not available: {e}")

logger = logging.getLogger(__name__)


def get_main_menu_keyboard(is_premium: bool = False) -> Optional[object]:
    """Главное меню бота."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        CallbackButton(text="Играть", payload="menu:play"),
    )
    builder.row(
        CallbackButton(text="Статистика", payload="menu:stats"),
    )
    builder.row(
        CallbackButton(text="Premium", payload="menu:premium"),
    )
    builder.row(
        CallbackButton(text="Помощь", payload="menu:help"),
    )
    
    return builder.as_markup()


def get_topics_keyboard() -> Optional[object]:
    """Выбор темы викторины."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    builder.row(CallbackButton(text="История", payload="topic:history"))
    builder.row(CallbackButton(text="Наука", payload="topic:science"))
    builder.row(CallbackButton(text="Спорт", payload="topic:sport"))
    builder.row(CallbackButton(text="География", payload="topic:geography"))
    builder.row(CallbackButton(text="Искусство", payload="topic:art"))
    builder.row(CallbackButton(text="Назад", payload="topic:back"))
    
    return builder.as_markup()


def get_stats_keyboard() -> Optional[object]:
    """Клавиатура статистики."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        CallbackButton(text="Обновить", payload="menu:stats"),
    )
    builder.row(
        CallbackButton(text="В меню", payload="menu:back"),
    )
    
    return builder.as_markup()


def get_premium_keyboard() -> Optional[object]:
    """Клавиатура Premium."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        CallbackButton(text="Оформить", payload="premium:buy"),
    )
    builder.row(
        CallbackButton(text="В меню", payload="menu:back"),
    )
    
    return builder.as_markup()


def get_answers_keyboard(answers: list, current_index: int, game_id: int) -> Optional[object]:
    """Клавиатура с вариантами ответов."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    for idx, answer in enumerate(answers[:4]):
        payload = f"answer:{game_id}:{current_index}:{idx}:False"
        builder.row(
            CallbackButton(text=f"{idx + 1}. {answer[:50]}", payload=payload)
        )
    
    return builder.as_markup()


def get_game_over_keyboard(game_id: int) -> Optional[object]:
    """Клавиатура конца игры."""
    if not MAXAPI_TYPES_AVAILABLE:
        return None
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        CallbackButton(text="Играть снова", payload="game:restart"),
    )
    builder.row(
        CallbackButton(text="Статистика", payload="menu:stats"),
    )
    
    return builder.as_markup()
