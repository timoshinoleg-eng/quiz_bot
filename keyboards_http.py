"""Улучшенные фабрики клавиатур для HTTP-клиента с эмодзи и UX-улучшениями."""
from typing import List, Dict, Optional


# === ЭМОДЗИ ДЛЯ КАТЕГОРИЙ ===
CATEGORY_EMOJIS = {
    'SCIENCE': '🔬',
    'HISTORY': '📜',
    'GEOGRAPHY': '🌍',
    'ART': '🎨',
    'SPORT': '⚽',
    'TECHNOLOGY': '💻',
    'NATURE': '🌿',
    'GENERAL': '❓'
}

# === ЭМОДЗИ ДЛЯ СЛОЖНОСТИ ===
DIFFICULTY_EMOJIS = {
    'EASY': '🟢',
    'MEDIUM': '🟡',
    'HARD': '🔴'
}

# === ЭМОДЗИ ДЛЯ БУКВ ОТВЕТОВ ===
ANSWER_EMOJIS = ['🔵', '🟢', '🟡', '🔴']


class KeyboardFactory:
    """
    Фабрика клавиатур для HTTP-клиента.
    Возвращает plain dict вместо Pydantic-моделей.
    """
    
    @staticmethod
    def callback_button(text: str, payload: str) -> Dict[str, str]:
        """Создание callback-кнопки."""
        if len(payload.encode('utf-8')) > 64:
            raise ValueError(f"Payload too long: {len(payload)} > 64 bytes")
        if len(text) > 64:
            text = text[:61] + "..."
        
        return {
            "type": "callback",
            "text": text,
            "payload": payload
        }
    
    @staticmethod
    def link_button(text: str, url: str) -> Dict[str, str]:
        """Создание кнопки-ссылки."""
        return {
            "type": "link",
            "text": text,
            "url": url
        }
    
    @staticmethod
    def row(*buttons: Dict[str, str]) -> List[Dict[str, str]]:
        """Создание ряда кнопок."""
        if len(buttons) > 7:
            raise ValueError(f"Too many buttons in row: {len(buttons)} > 7")
        return list(buttons)
    
    @staticmethod
    def keyboard(*rows: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """Создание клавиатуры из рядов."""
        if len(rows) > 30:
            raise ValueError(f"Too many rows: {len(rows)} > 30")
        return list(rows)
    
    @staticmethod
    def info_button(text: str) -> Dict[str, str]:
        """Информационная кнопка (без действия)."""
        return {
            "type": "callback",
            "text": text,
            "payload": "info:no_action"
        }


def get_answers_keyboard_http(
    answers: List[str], 
    current_index: int, 
    game_id: int, 
    correct_index: int,
    total_questions: int = 10
) -> List[List[Dict[str, str]]]:
    """Улучшенная клавиатура с вариантами ответов (с эмодзи и прогрессом)."""
    buttons = []
    
    for idx, answer in enumerate(answers[:4]):
        payload = f"answer:{game_id}:{current_index}:{idx}:{correct_index}"
        emoji = ANSWER_EMOJIS[idx] if idx < len(ANSWER_EMOJIS) else '⚪'
        # Обрезаем ответ до 55 символов (оставляем место для эмодзи и буквы)
        display_text = f"{emoji} {chr(65 + idx)}. {answer[:50]}"
        buttons.append(KeyboardFactory.callback_button(display_text, payload))
    
    # Раскладка: 2 кнопки в ряд для мобильных
    rows = []
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            rows.append(KeyboardFactory.row(buttons[i], buttons[i + 1]))
        else:
            rows.append(KeyboardFactory.row(buttons[i]))
    
    # Добавляем кнопку пропуска
    rows.append(KeyboardFactory.row(
        KeyboardFactory.callback_button("⏭ Пропустить", f"skip:{game_id}:{current_index}")
    ))
    
    # Добавляем индикатор прогресса
    progress = current_index + 1
    progress_bar = "█" * progress + "░" * (total_questions - progress)
    rows.append(KeyboardFactory.row(
        KeyboardFactory.info_button(f"📊 {progress}/{total_questions} {progress_bar[:10]}")
    ))
    
    return KeyboardFactory.keyboard(*rows)


def get_game_over_keyboard_http(game_id: int, score: int, total: int) -> List[List[Dict[str, str]]]:
    """Улучшенная клавиатура конца игры."""
    percentage = (score / total * 100) if total > 0 else 0
    
    # Эмодзи в зависимости от результата
    if percentage >= 90:
        emoji = "🏆"
        title = "ВЕЛИКОЛЕПНО!"
    elif percentage >= 70:
        emoji = "🌟"
        title = "ОТЛИЧНО!"
    elif percentage >= 50:
        emoji = "👍"
        title = "ХОРОШО!"
    else:
        emoji = "💪"
        title = "ПОПРОБУЙ ЕЩЁ!"
    
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{emoji} {title}", "game:restart")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("📊 Статистика", "menu:stats"),
            KeyboardFactory.callback_button("🏆 Рейтинг", "menu:leaderboard")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("📤 Поделиться", f"share:{game_id}"),
            KeyboardFactory.callback_button("⬅️ В меню", "menu:back")
        ),
    )


def get_stats_keyboard_http() -> List[List[Dict[str, str]]]:
    """Клавиатура статистики."""
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(KeyboardFactory.callback_button("🔄 Обновить", "menu:stats")),
        KeyboardFactory.row(KeyboardFactory.callback_button("⬅️ В меню", "menu:back")),
    )


def get_premium_keyboard_http() -> List[List[Dict[str, str]]]:
    """Клавиатура Premium."""
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(KeyboardFactory.callback_button("💳 Оформить Premium", "premium:buy")),
        KeyboardFactory.row(KeyboardFactory.callback_button("⬅️ В меню", "menu:back")),
    )


# === Фабричные функции для викторины ===

def get_main_menu_keyboard_http(is_premium: bool = False) -> List[List[Dict[str, str]]]:
    """Улучшенное главное меню."""
    rows = [
        KeyboardFactory.row(
            KeyboardFactory.callback_button("🎮 Играть", "menu:play")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("📊 Статистика", "menu:stats"),
            KeyboardFactory.callback_button("⚙️ Настройки", "menu:settings")
        ),
    ]
    
    if is_premium:
        rows.insert(0, KeyboardFactory.row(
            KeyboardFactory.callback_button("⭐ Премиум-режим", "menu:premium")
        ))
    
    return KeyboardFactory.keyboard(*rows)


def get_quiz_keyboard_http(
    question_id: int, 
    options: List[str],
    question_number: int = 1,
    total_questions: int = 10,
    category: str = None,
    difficulty: str = None
) -> List[List[Dict[str, str]]]:
    """Улучшенная клавиатура вопроса с прогрессом."""
    buttons = []
    
    for i, opt in enumerate(options):
        payload = f"quiz:{question_id}:{chr(65 + i).lower()}"
        emoji = ANSWER_EMOJIS[i] if i < len(ANSWER_EMOJIS) else '⚪'
        # Обрезаем длинные варианты
        opt_short = opt[:50] if len(opt) > 50 else opt
        text = f"{emoji} {chr(65 + i)}. {opt_short}"
        buttons.append(KeyboardFactory.callback_button(text, payload))
    
    # Раскладка: 2 кнопки в ряд
    rows = []
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            rows.append(KeyboardFactory.row(buttons[i], buttons[i + 1]))
        else:
            rows.append(KeyboardFactory.row(buttons[i]))
    
    # Кнопка пропуска
    rows.append(KeyboardFactory.row(
        KeyboardFactory.callback_button("⏭ Пропустить", f"skip:{question_id}")
    ))
    
    # Информация о прогрессе с эмодзи категории и сложности
    cat_emoji = CATEGORY_EMOJIS.get(category, '❓') if category else '❓'
    diff_emoji = DIFFICULTY_EMOJIS.get(difficulty, '⚪') if difficulty else '⚪'
    progress_bar = "█" * question_number + "░" * (total_questions - question_number)
    
    rows.append(KeyboardFactory.row(
        KeyboardFactory.info_button(
            f"{cat_emoji}{diff_emoji} {question_number}/{total_questions} {progress_bar[:8]}"
        )
    ))
    
    return KeyboardFactory.keyboard(*rows)


def get_result_keyboard_http(score: int, total: int, game_id: int = None) -> List[List[Dict[str, str]]]:
    """Улучшенная клавиатура результата с визуальной иерархией."""
    percentage = (score / total * 100) if total > 0 else 0
    
    # Эмодзи и заголовок в зависимости от результата
    if percentage >= 90:
        emoji = "🏆"
        title = "ВЕЛИКОЛЕПНО!"
    elif percentage >= 70:
        emoji = "🌟"
        title = "ОТЛИЧНО!"
    elif percentage >= 50:
        emoji = "👍"
        title = "ХОРОШО!"
    else:
        emoji = "💪"
        title = "ПОПРОБУЙ ЕЩЁ!"
    
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{emoji} {title}", "menu:play")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("📊 Статистика", "menu:stats"),
            KeyboardFactory.callback_button("🏆 Рейтинг", "menu:leaderboard")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("📤 Поделиться", f"share:{score}:{total}"),
            KeyboardFactory.callback_button("⬅️ В меню", "menu:back")
        )
    )


def get_topics_keyboard_http() -> List[List[Dict[str, str]]]:
    """Улучшенный выбор темы с эмодзи."""
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['HISTORY']} История", "topic:history"),
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['SCIENCE']} Наука", "topic:science")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['SPORT']} Спорт", "topic:sport"),
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['GEOGRAPHY']} География", "topic:geography")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['ART']} Искусство", "topic:art"),
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['TECHNOLOGY']} Технологии", "topic:technology")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['NATURE']} Природа", "topic:nature"),
            KeyboardFactory.callback_button(f"{CATEGORY_EMOJIS['GENERAL']} Общие", "topic:general")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("⬅️ Назад", "topic:back")
        ),
    )


def get_difficulty_keyboard_http() -> List[List[Dict[str, str]]]:
    """Улучшенный выбор сложности с эмодзи."""
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{DIFFICULTY_EMOJIS['EASY']} Легко", "difficulty:easy")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{DIFFICULTY_EMOJIS['MEDIUM']} Средне", "difficulty:medium")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button(f"{DIFFICULTY_EMOJIS['HARD']} Сложно", "difficulty:hard")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("⬅️ Назад", "difficulty:back")
        ),
    )


def get_question_count_keyboard_http() -> List[List[Dict[str, str]]]:
    """Улучшенный выбор количества вопросов."""
    return KeyboardFactory.keyboard(
        KeyboardFactory.row(
            KeyboardFactory.callback_button("5 🎯", "count:5"),
            KeyboardFactory.callback_button("10 ⭐", "count:10")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("15 🏆", "count:15"),
            KeyboardFactory.callback_button("20 💎", "count:20")
        ),
        KeyboardFactory.row(
            KeyboardFactory.callback_button("⬅️ Назад", "count:back")
        ),
    )


def get_feedback_keyboard_http(is_correct: bool, correct_answer: str = None) -> List[List[Dict[str, str]]]:
    """Клавиатура для фидбека после ответа."""
    if is_correct:
        return KeyboardFactory.keyboard(
            KeyboardFactory.row(
                KeyboardFactory.callback_button("✅ Правильно! Следующий →", "next:question")
            )
        )
    else:
        return KeyboardFactory.keyboard(
            KeyboardFactory.row(
                KeyboardFactory.callback_button(f"❌ Правильно: {correct_answer[:40]}", "info:correct")
            ),
            KeyboardFactory.row(
                KeyboardFactory.callback_button("→ Следующий вопрос", "next:question")
            )
        )
