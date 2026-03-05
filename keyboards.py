"""Inline-клавиатуры для MAX-Квиз (собственные Pydantic модели для maxapi 0.9.15).

Используем собственные модели вместо встроенных CallbackButton/ChatButton 
из-за бага с discriminator в Union-типах maxapi 0.9.15.
"""
import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Импортируем Attachment для наследования
try:
    from maxapi.types import Attachment
    MAXAPI_AVAILABLE = True
except ImportError:
    MAXAPI_AVAILABLE = False
    Attachment = BaseModel

logger = logging.getLogger(__name__)


class InlineKeyboardButton(BaseModel):
    """Универсальная модель кнопки inline-клавиатуры.
    
    ЗАМЕНЯЕТ неработающие CallbackButton/ChatButton из maxapi.types.
    """
    type: Literal["callback", "link", "request_contact", "request_geo_location"] = "callback"
    text: str = Field(..., min_length=1, max_length=64, description="Текст на кнопке")
    payload: Optional[str] = Field(default=None, max_length=64, description="Данные для callback")
    
    @classmethod
    def callback(cls, text: str, payload: str) -> "InlineKeyboardButton":
        """Фабричный метод для создания callback-кнопки."""
        return cls(type="callback", text=text, payload=payload)


class InlineKeyboardPayload(BaseModel):
    """Содержимое payload для inline-клавиатуры."""
    buttons: List[List[InlineKeyboardButton]]  # двумерный массив: ряды → кнопки
    
    @classmethod
    def vertical(cls, *buttons: InlineKeyboardButton) -> "InlineKeyboardPayload":
        """Вертикальный список кнопок (по одной в ряду)."""
        return cls(buttons=[[btn] for btn in buttons])


class InlineKeyboardAttachment(Attachment):
    """Полное вложение inline-клавиатуры для передачи в send_message.
    
    Наследуется от Attachment для совместимости с maxapi 0.9.15.
    """
    type: Literal["inline_keyboard"] = Field(default="inline_keyboard", frozen=True)
    payload: InlineKeyboardPayload
    
    @classmethod
    def from_buttons(cls, *buttons: InlineKeyboardButton) -> "InlineKeyboardAttachment":
        """Быстрое создание клавиатуры из кнопок (вертикальный список)."""
        return cls(payload=InlineKeyboardPayload.vertical(*buttons))


# === ФАБРИЧНЫЕ ФУНКЦИИ ДЛЯ БОТА ===

def get_main_menu_keyboard(is_premium: bool = False) -> Optional[InlineKeyboardAttachment]:
    """Главное меню бота."""
    if not MAXAPI_AVAILABLE:
        return None
    
    return InlineKeyboardAttachment.from_buttons(
        InlineKeyboardButton.callback("Начать игру", "menu:play"),
        InlineKeyboardButton.callback("Статистика", "menu:stats"),
        InlineKeyboardButton.callback("Premium", "menu:premium"),
        InlineKeyboardButton.callback("Помощь", "menu:help"),
    )


def get_topics_keyboard() -> Optional[InlineKeyboardAttachment]:
    """Выбор темы викторины."""
    if not MAXAPI_AVAILABLE:
        return None
    
    return InlineKeyboardAttachment.from_buttons(
        InlineKeyboardButton.callback("История", "topic:history"),
        InlineKeyboardButton.callback("Наука", "topic:science"),
        InlineKeyboardButton.callback("Спорт", "topic:sport"),
        InlineKeyboardButton.callback("География", "topic:geography"),
        InlineKeyboardButton.callback("Искусство", "topic:art"),
        InlineKeyboardButton.callback("Назад", "topic:back"),
    )


def get_stats_keyboard() -> Optional[InlineKeyboardAttachment]:
    """Клавиатура статистики."""
    if not MAXAPI_AVAILABLE:
        return None
    
    return InlineKeyboardAttachment.from_buttons(
        InlineKeyboardButton.callback("Обновить", "menu:stats"),
        InlineKeyboardButton.callback("В меню", "menu:back"),
    )


def get_premium_keyboard() -> Optional[InlineKeyboardAttachment]:
    """Клавиатура Premium."""
    if not MAXAPI_AVAILABLE:
        return None
    
    return InlineKeyboardAttachment.from_buttons(
        InlineKeyboardButton.callback("Оформить", "premium:buy"),
        InlineKeyboardButton.callback("В меню", "menu:back"),
    )


def get_answers_keyboard(answers: List[str], current_index: int, game_id: int) -> Optional[InlineKeyboardAttachment]:
    """Клавиатура с вариантами ответов."""
    if not MAXAPI_AVAILABLE:
        return None
    
    buttons = []
    for idx, answer in enumerate(answers[:4]):
        payload = f"answer:{game_id}:{current_index}:{idx}:False"
        buttons.append(InlineKeyboardButton.callback(f"{idx + 1}. {answer[:50]}", payload))
    
    return InlineKeyboardAttachment.from_buttons(*buttons)


def get_game_over_keyboard(game_id: int) -> Optional[InlineKeyboardAttachment]:
    """Клавиатура конца игры."""
    if not MAXAPI_AVAILABLE:
        return None
    
    return InlineKeyboardAttachment.from_buttons(
        InlineKeyboardButton.callback("Играть снова", "game:restart"),
        InlineKeyboardButton.callback("Статистика", "menu:stats"),
    )
