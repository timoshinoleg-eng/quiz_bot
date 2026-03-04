"""Inline-клавиатуры для бота.

Этот модуль содержит все клавиатуры, используемые в боте.
Все клавиатуры возвращаются в формате словаря для maxapi.

Example:
    >>> from keyboards import get_topics_keyboard, get_answers_keyboard
    >>> kb = get_topics_keyboard()
    >>> await message.reply("Выберите тему:", reply_markup=kb)
"""

from typing import List, Optional, Dict, Any

from models import QuestionCategory, DifficultyLevel


def _create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
    """Создаёт inline клавиатуру.
    
    Args:
        buttons: Список рядов кнопок
        
    Returns:
        Dict: Объект клавиатуры для API
    """
    return {
        "inline_keyboard": buttons
    }


def get_main_menu_keyboard(is_premium: bool = False) -> Dict[str, Any]:
    """Главное меню бота.
    
    Args:
        is_premium: Есть ли у пользователя Premium
        
    Returns:
        Dict: Клавиатура главного меню
    """
    buttons = [
        [{"text": "🎮 Играть", "callback_data": "menu:play"}],
        [{"text": "⚔️ Дуэль с другом", "callback_data": "menu:duel"}],
        [{"text": "📊 Статистика", "callback_data": "menu:stats"}],
    ]
    
    if not is_premium:
        buttons.append([{"text": "⭐ Купить Premium", "callback_data": "menu:premium"}])
    else:
        buttons.append([{"text": "⭐ Мой Premium", "callback_data": "menu:premium_info"}])
    
    buttons.append([{"text": "❓ Помощь", "callback_data": "menu:help"}])
    
    return _create_inline_keyboard(buttons)


def get_topics_keyboard() -> Dict[str, Any]:
    """Клавиатура выбора темы.
    
    Returns:
        Dict: Клавиатура с категориями
    """
    buttons = [
        [{"text": "📜 История", "callback_data": "topic:history"}],
        [{"text": "🔬 Наука", "callback_data": "topic:science"}],
        [{"text": "🎨 Искусство", "callback_data": "topic:art"}],
        [{"text": "⚽ Спорт", "callback_data": "topic:sports"}],
        [{"text": "🌍 География", "callback_data": "topic:geography"}],
        [{"text": "🎬 Развлечения", "callback_data": "topic:entertainment"}],
        [{"text": "📚 Общие знания", "callback_data": "topic:general"}],
        [{"text": "🔙 Назад", "callback_data": "topic:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_difficulty_keyboard() -> Dict[str, Any]:
    """Клавиатура выбора сложности.
    
    Returns:
        Dict: Клавиатура со сложностями
    """
    buttons = [
        [{"text": "🟢 Легко", "callback_data": "diff:easy"}],
        [{"text": "🟡 Средне", "callback_data": "diff:medium"}],
        [{"text": "🔴 Сложно", "callback_data": "diff:hard"}],
        [{"text": "🔙 Назад", "callback_data": "diff:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_question_count_keyboard() -> Dict[str, Any]:
    """Клавиатура выбора количества вопросов.
    
    Returns:
        Dict: Клавиатура с вариантами
    """
    buttons = [
        [
            {"text": "5", "callback_data": "count:5"},
            {"text": "10", "callback_data": "count:10"},
            {"text": "15", "callback_data": "count:15"},
        ],
        [{"text": "🔙 Назад", "callback_data": "count:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_answers_keyboard(
    answers: List[tuple],
    question_index: int,
    game_id: int
) -> Dict[str, Any]:
    """Клавиатура с вариантами ответов.
    
    Args:
        answers: Список (текст ответа, is_correct)
        question_index: Номер текущего вопроса
        game_id: ID игры
        
    Returns:
        Dict: Клавиатура с ответами
    """
    buttons = []
    
    for i, (answer_text, is_correct) in enumerate(answers):
        # Обрезаем длинные ответы
        display_text = answer_text[:30] + "..." if len(answer_text) > 30 else answer_text
        
        callback = f"answer:{game_id}:{question_index}:{i}:{is_correct}"
        buttons.append([{"text": display_text, "callback_data": callback}])
    
    # Добавляем кнопку подсказки (если есть)
    buttons.append([{"text": "💡 Подсказка", "callback_data": f"hint:{game_id}"}])
    
    return _create_inline_keyboard(buttons)


def get_game_over_keyboard(game_id: int) -> Dict[str, Any]:
    """Клавиатура после завершения игры.
    
    Args:
        game_id: ID игры
        
    Returns:
        Dict: Клавиатура с опциями
    """
    buttons = [
        [{"text": "🔄 Играть ещё", "callback_data": f"game:restart:{game_id}"}],
        [{"text": "📤 Поделиться результатом", "callback_data": f"game:share:{game_id}"}],
        [{"text": "🏠 Главное меню", "callback_data": "game:menu"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_duel_menu_keyboard() -> Dict[str, Any]:
    """Меню дуэли.
    
    Returns:
        Dict: Клавиатура меню дуэли
    """
    buttons = [
        [{"text": "⚔️ Создать дуэль", "callback_data": "duel:create"}],
        [{"text": "🔗 Присоединиться", "callback_data": "duel:join"}],
        [{"text": "📋 Список дуэлей", "callback_data": "duel:list"}],
        [{"text": "🔙 Назад", "callback_data": "duel:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_duel_topics_keyboard() -> Dict[str, Any]:
    """Клавиатура выбора темы для дуэли.
    
    Returns:
        Dict: Клавиатура с категориями
    """
    # Упрощённая версия - меньше категорий для дуэлей
    buttons = [
        [
            {"text": "📜 История", "callback_data": "duel_topic:history"},
            {"text": "🔬 Наука", "callback_data": "duel_topic:science"},
        ],
        [
            {"text": "⚽ Спорт", "callback_data": "duel_topic:sports"},
            {"text": "🌍 География", "callback_data": "duel_topic:geography"},
        ],
        [{"text": "🔙 Назад", "callback_data": "duel_topic:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_premium_keyboard() -> Dict[str, Any]:
    """Клавиатура для покупки Premium.
    
    Returns:
        Dict: Клавиатура покупки
    """
    buttons = [
        [{"text": "⭐ Купить Premium - 349₽/мес", "callback_data": "premium:buy"}],
        [{"text": "📋 Что входит в Premium", "callback_data": "premium:info"}],
        [{"text": "🔙 Назад", "callback_data": "premium:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_payment_keyboard(payment_url: str) -> Dict[str, Any]:
    """Клавиатура для оплаты.
    
    Args:
        payment_url: URL для оплаты
        
    Returns:
        Dict: Клавиатура оплаты
    """
    buttons = [
        [{"text": "💳 Перейти к оплате", "url": payment_url}],
        [{"text": "🔙 Отмена", "callback_data": "payment:cancel"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_stats_keyboard() -> Dict[str, Any]:
    """Клавиатура статистики.
    
    Returns:
        Dict: Клавиатура статистики
    """
    buttons = [
        [{"text": "📊 Моя статистика", "callback_data": "stats:personal"}],
        [{"text": "🏆 Топ игроков", "callback_data": "stats:leaderboard"}],
        [{"text": "📈 Прогресс", "callback_data": "stats:progress"}],
        [{"text": "🔙 Назад", "callback_data": "stats:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_hint_keyboard(hint_type: str, game_id: int) -> Dict[str, Any]:
    """Клавиатура для подсказки.
    
    Args:
        hint_type: Тип подсказки (50_50, time, skip)
        game_id: ID игры
        
    Returns:
        Dict: Клавиатура подсказки
    """
    buttons = []
    
    if hint_type == "50_50":
        buttons.append([{"text": "50/50 - Убрать 2 ответа", "callback_data": f"hint_use:50_50:{game_id}"}])
    elif hint_type == "time":
        buttons.append([{"text": "⏱️ +15 секунд", "callback_data": f"hint_use:time:{game_id}"}])
    elif hint_type == "skip":
        buttons.append([{"text": "⏭️ Пропустить вопрос", "callback_data": f"hint_use:skip:{game_id}"}])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": f"hint_use:back:{game_id}"}])
    
    return _create_inline_keyboard(buttons)


def get_confirm_keyboard(action: str, item_id: int) -> Dict[str, Any]:
    """Клавиатура подтверждения.
    
    Args:
        action: Действие для подтверждения
        item_id: ID элемента
        
    Returns:
        Dict: Клавиатура подтверждения
    """
    buttons = [
        [
            {"text": "✅ Да", "callback_data": f"confirm:{action}:{item_id}:yes"},
            {"text": "❌ Нет", "callback_data": f"confirm:{action}:{item_id}:no"},
        ],
    ]
    
    return _create_inline_keyboard(buttons)


def get_help_keyboard() -> Dict[str, Any]:
    """Клавиатура помощи.
    
    Returns:
        Dict: Клавиатура помощи
    """
    buttons = [
        [{"text": "🎮 Как играть", "callback_data": "help:how_to_play"}],
        [{"text": "⭐ О Premium", "callback_data": "help:premium"}],
        [{"text": "⚔️ О дуэлях", "callback_data": "help:duels"}],
        [{"text": "💡 Подсказки", "callback_data": "help:hints"}],
        [{"text": "🔙 Назад", "callback_data": "help:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def get_leaderboard_keyboard(period: str = "all") -> Dict[str, Any]:
    """Клавиатура для переключения периода лидерборда.
    
    Args:
        period: Текущий период (day, week, month, all)
        
    Returns:
        Dict: Клавиатура лидерборда
    """
    buttons = [
        [
            {"text": "📅 День", "callback_data": "leaderboard:day"},
            {"text": "📆 Неделя", "callback_data": "leaderboard:week"},
        ],
        [
            {"text": "📊 Месяц", "callback_data": "leaderboard:month"},
            {"text": "🏆 Всё время", "callback_data": "leaderboard:all"},
        ],
        [{"text": "🔙 Назад", "callback_data": "leaderboard:back"}],
    ]
    
    return _create_inline_keyboard(buttons)


def remove_keyboard() -> Dict[str, Any]:
    """Возвращает пустую клавиатуру (для удаления).
    
    Returns:
        Dict: Пустая клавиатура
    """
    return _create_inline_keyboard([])


# Маппинг категорий для отображения
CATEGORY_EMOJI = {
    QuestionCategory.HISTORY: "📜",
    QuestionCategory.SCIENCE: "🔬",
    QuestionCategory.ART: "🎨",
    QuestionCategory.SPORTS: "⚽",
    QuestionCategory.GEOGRAPHY: "🌍",
    QuestionCategory.ENTERTAINMENT: "🎬",
    QuestionCategory.GENERAL: "📚",
}

DIFFICULTY_EMOJI = {
    DifficultyLevel.EASY: "🟢",
    DifficultyLevel.MEDIUM: "🟡",
    DifficultyLevel.HARD: "🔴",
}


def format_category(category: QuestionCategory) -> str:
    """Форматирует категорию для отображения.
    
    Args:
        category: Категория
        
    Returns:
        str: Отформатированная строка
    """
    emoji = CATEGORY_EMOJI.get(category, "❓")
    names = {
        QuestionCategory.HISTORY: "История",
        QuestionCategory.SCIENCE: "Наука",
        QuestionCategory.ART: "Искусство",
        QuestionCategory.SPORTS: "Спорт",
        QuestionCategory.GEOGRAPHY: "География",
        QuestionCategory.ENTERTAINMENT: "Развлечения",
        QuestionCategory.GENERAL: "Общие знания",
    }
    return f"{emoji} {names.get(category, category.value)}"


def format_difficulty(difficulty: DifficultyLevel) -> str:
    """Форматирует сложность для отображения.
    
    Args:
        difficulty: Сложность
        
    Returns:
        str: Отформатированная строка
    """
    emoji = DIFFICULTY_EMOJI.get(difficulty, "⚪")
    names = {
        DifficultyLevel.EASY: "Легко",
        DifficultyLevel.MEDIUM: "Средне",
        DifficultyLevel.HARD: "Сложно",
    }
    return f"{emoji} {names.get(difficulty, difficulty.value)}"
