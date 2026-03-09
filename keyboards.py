"""Inline-клавиатуры для MAX-Квиз (Pydantic модели для maxapi 0.9.15+).

ВАЖНО: Используются собственные Pydantic-модели вместо встроенных из maxapi.types,
т.к. встроенные CallbackButton/ChatButton имеют баг с Union-типами (ChatButton требует chat_title).
"""
import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from maxapi.types import Attachment

logger = logging.getLogger(__name__)


class InlineKeyboardButton(BaseModel):
    """Собственная модель кнопки inline-клавиатуры.
    
    НЕ используем maxapi.types.CallbackButton из-за бага с Union-типами!
    """
    type: Literal["callback", "link", "request_contact", "request_geo_location", "open_app"] = "callback"
    text: str = Field(..., min_length=1, max_length=64, description="Текст на кнопке")
    payload: Optional[str] = Field(default=None, max_length=64, description="Данные для callback")
    url: Optional[str] = Field(default=None, description="URL для link-кнопки")
    
    @classmethod
    def callback(cls, text: str, payload: str) -> "InlineKeyboardButton":
        """Фабричный метод для создания callback-кнопки."""
        return cls(type="callback", text=text, payload=payload)
    
    @classmethod
    def link(cls, text: str, url: str) -> "InlineKeyboardButton":
        """Фабричный метод для создания ссылочной кнопки."""
        return cls(type="link", text=text, url=url)


class InlineKeyboardRow(BaseModel):
    """Ряд кнопок inline-клавиатуры."""
    buttons: List[InlineKeyboardButton] = Field(..., max_length=7, description="Кнопки в ряду (max 7)")
    
    @classmethod
    def single(cls, button: InlineKeyboardButton) -> "InlineKeyboardRow":
        """Создает ряд с одной кнопкой."""
        return cls(buttons=[button])
    
    @classmethod
    def pair(cls, left: InlineKeyboardButton, right: InlineKeyboardButton) -> "InlineKeyboardRow":
        """Создает ряд с двумя кнопками."""
        return cls(buttons=[left, right])


class InlineKeyboardPayload(BaseModel):
    """Содержимое payload для inline-клавиатуры."""
    buttons: List[List[InlineKeyboardButton]]
    
    @field_validator('buttons')
    @classmethod
    def validate_limits(cls, v):
        """Проверка ограничений MAX API."""
        if len(v) > 30:
            raise ValueError(f"Too many rows: {len(v)} > 30")
        total = sum(len(row) for row in v)
        if total > 210:
            raise ValueError(f"Too many buttons: {total} > 210")
        for row in v:
            if len(row) > 7:
                raise ValueError(f"Too many buttons in row: {len(row)} > 7")
        return v
    
    @classmethod
    def from_rows(cls, *rows: InlineKeyboardRow) -> "InlineKeyboardPayload":
        """Создает payload из рядов кнопок."""
        return cls(buttons=[row.buttons for row in rows])


class InlineKeyboardAttachment(Attachment):
    """Вложение inline-клавиатуры для передачи в send_message.
    
    Наследуется от Attachment для совместимости с API.
    """
    type: Literal["inline_keyboard"] = Field(default="inline_keyboard", frozen=True)
    payload: InlineKeyboardPayload
    
    def model_dump(self, **kwargs):
        """Явная реализация сериализации — КРИТИЧЕСКИ ВАЖНО!"""
        return {
            "type": self.type,
            "payload": self.payload.model_dump(**kwargs)
        }
    
    @classmethod
    def from_rows(cls, *rows: InlineKeyboardRow) -> "InlineKeyboardAttachment":
        """Создает клавиатуру из рядов."""
        return cls(payload=InlineKeyboardPayload.from_rows(*rows))


# === ФАБРИЧНЫЕ ФУНКЦИИ ДЛЯ БОТА ===

def get_main_menu_keyboard(is_premium: bool = False) -> InlineKeyboardAttachment:
    """Главное меню бота."""
    rows = [
        InlineKeyboardRow.single(
            InlineKeyboardButton.callback("🎮 Начать игру", "menu:play")
        ),
        InlineKeyboardRow.pair(
            InlineKeyboardButton.callback("📊 Статистика", "menu:stats"),
            InlineKeyboardButton.callback("⭐ Premium", "menu:premium")
        ),
        InlineKeyboardRow.single(
            InlineKeyboardButton.callback("❓ Помощь", "menu:help")
        ),
    ]
    return InlineKeyboardAttachment.from_rows(*rows)


def get_topics_keyboard() -> InlineKeyboardAttachment:
    """Выбор темы викторины."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.single(InlineKeyboardButton.callback("📜 История", "topic:history")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🔬 Наука", "topic:science")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⚽ Спорт", "topic:sport")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🌍 География", "topic:geography")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🎨 Искусство", "topic:art")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ Назад", "topic:back")),
    )


def get_stats_keyboard() -> InlineKeyboardAttachment:
    """Клавиатура статистики."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🔄 Обновить", "menu:stats")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ В меню", "menu:back")),
    )


def get_premium_keyboard() -> InlineKeyboardAttachment:
    """Клавиатура Premium."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.single(InlineKeyboardButton.callback("💳 Оформить", "premium:buy")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ В меню", "menu:back")),
    )


def get_difficulty_keyboard() -> InlineKeyboardAttachment:
    """Клавиатура выбора сложности."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🟢 Легко", "difficulty:easy")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🟡 Средне", "difficulty:medium")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("🔴 Сложно", "difficulty:hard")),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ Назад", "difficulty:back")),
    )


def get_question_count_keyboard() -> InlineKeyboardAttachment:
    """Клавиатура выбора количества вопросов."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.pair(
            InlineKeyboardButton.callback("5", "count:5"),
            InlineKeyboardButton.callback("10", "count:10")
        ),
        InlineKeyboardRow.pair(
            InlineKeyboardButton.callback("15", "count:15"),
            InlineKeyboardButton.callback("20", "count:20")
        ),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ Назад", "count:back")),
    )


def get_answers_keyboard(answers: List[str], current_index: int, game_id: int, correct_index: int) -> InlineKeyboardAttachment:
    """Клавиатура с вариантами ответов."""
    buttons = []
    for idx, answer in enumerate(answers[:4]):
        payload = f"answer:{game_id}:{current_index}:{idx}:{correct_index}"
        display_text = f"{idx + 1}. {answer[:50]}"
        buttons.append(InlineKeyboardButton.callback(display_text, payload))
    
    rows = []
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            rows.append(InlineKeyboardRow.pair(buttons[i], buttons[i + 1]))
        else:
            rows.append(InlineKeyboardRow.single(buttons[i]))
    
    return InlineKeyboardAttachment.from_rows(*rows)


def get_game_over_keyboard(game_id: int, score: int, total: int) -> InlineKeyboardAttachment:
    """Клавиатура конца игры."""
    return InlineKeyboardAttachment.from_rows(
        InlineKeyboardRow.pair(
            InlineKeyboardButton.callback("🔄 Играть снова", "game:restart"),
            InlineKeyboardButton.callback("📊 Статистика", "menu:stats")
        ),
        InlineKeyboardRow.single(InlineKeyboardButton.callback("⬅️ В меню", "menu:back")),
    )
