#!/usr/bin/env python3
"""
Исправление ВСЕХ неправильных ответов в базе данных.
Обновляет все 2820 вопросов с правдоподобными неправильными вариантами.
"""

import sqlite3
import json
import random
import re

COUNTRY_WRONG_ANSWERS = [
    'Перу', 'Аргентина', 'Бразилия', 'Колумбия', 'Мексика',
    'Испания', 'Португалия', 'Италия', 'Франция', 'Германия',
    'Великобритания', 'США', 'Канада', 'Австралия', 'Япония',
    'Китай', 'Индия', 'Россия', 'Египет', 'Турция'
]

CITY_WRONG_ANSWERS = [
    'Париж', 'Лондон', 'Берлин', 'Мадрид', 'Рим',
    'Вена', 'Прага', 'Варшава', 'Амстердам', 'Брюссель',
    'Москва', 'Санкт-Петербург', 'Киев', 'Минск', 'Токио',
    'Пекин', 'Дели', 'Каир', 'Стамбул', 'Нью-Йорк'
]

PERSON_WRONG_ANSWERS = [
    'Альберт Эйнштейн', 'Исаак Ньютон', 'Чарльз Дарвин',
    'Леонардо да Винчи', 'Микеланджело', 'Пабло Пикассо',
    'Уильям Шекспир', 'Лев Толстой', 'Фёдор Достоевский',
    'Наполеон Бонапарт', 'Александр Пушкин', 'Вольфганг Моцарт'
]

YEAR_WRONG_ANSWERS = ['1914', '1939', '1945', '1812', '1700', '1800', '1900', '1950', '1960', '1970']

SCIENCE_ELEMENTS = ['Кислород', 'Водород', 'Углерод', 'Азот', 'Железо', 'Медь', 'Золото', 'Серебро']

SPORT_TEAMS = ['Спартак', 'ЦСКА', 'Зенит', 'Барселона', 'Реал Мадрид', 'Манчестер', 'Ливерпуль', 'Ювентус']

ANIMALS = ['лев', 'тигр', 'слон', 'жираф', 'зебра', 'медведь', 'волк', 'лиса', 'орел', 'акула']

CATEGORY_MAP = {
    'GEOGRAPHY': {
        'keywords': ['страна', 'город', 'столица', 'река', 'море', 'остров', 'континент', 'гора'],
        'wrong_pool': COUNTRY_WRONG_ANSWERS + CITY_WRONG_ANSWERS
    },
    'HISTORY': {
        'keywords': ['год', 'война', 'царь', 'император', 'революция', 'битва', 'век', 'история'],
        'wrong_pool': PERSON_WRONG_ANSWERS + YEAR_WRONG_ANSWERS
    },
    'SCIENCE': {
        'keywords': ['физика', 'химия', 'биология', 'атом', 'молекула', 'энергия', 'наука', 'планета'],
        'wrong_pool': SCIENCE_ELEMENTS + PERSON_WRONG_ANSWERS[:6]
    },
    'ART': {
        'keywords': ['художник', 'картина', 'музыка', 'писатель', 'книга', 'фильм', 'роман', 'поэт'],
        'wrong_pool': PERSON_WRONG_ANSWERS
    },
    'SPORT': {
        'keywords': ['футбол', 'хоккей', 'олимпиада', 'чемпион', 'команда', 'игрок', 'спорт'],
        'wrong_pool': SPORT_TEAMS + PERSON_WRONG_ANSWERS[:6]
    },
    'NATURE': {
        'keywords': ['животное', 'птица', 'растение', 'дерево', 'лес', 'природа', 'зверь'],
        'wrong_pool': ANIMALS
    },
}

def get_category_from_question(text: str) -> str:
    """Определение категории по тексту вопроса."""
    text_lower = text.lower()
    
    for category, config in CATEGORY_MAP.items():
        if any(kw in text_lower for kw in config['keywords']):
            return category
    
    return 'GENERAL'

def generate_wrong_answers(correct_answer: str, question_text: str, category: str) -> list:
    """Генерация неправильных ответов."""
    wrong = []
    
    # Определить категорию если GENERAL
    if category == 'GENERAL':
        category = get_category_from_question(question_text)
    
    # Стратегия 1: Пул категории
    if category in CATEGORY_MAP:
        pool = CATEGORY_MAP[category]['wrong_pool'][:]
        pool = [a for a in pool if a.lower() != correct_answer.lower()]
        if len(pool) >= 3:
            wrong = random.sample(pool, 3)
            return wrong
    
    # Стратегия 2: Год (4 цифры)
    numbers = re.findall(r'\d{4}', correct_answer)
    if numbers and not wrong:
        year = int(numbers[0])
        wrong = [str(year - 1), str(year + 1), str(year - 5)]
        return wrong
    
    # Стратегия 3: Число
    numbers = re.findall(r'\d+', correct_answer)
    if numbers and not wrong:
        num = int(numbers[0])
        wrong = [str(num - 1), str(num + 1), str(num + 10)]
        if len(correct_answer) > len(str(num)):
            wrong = [correct_answer.replace(str(num), w) for w in wrong]
        return wrong
    
    # Стратегия 4: Fallback
    if not wrong:
        all_names = COUNTRY_WRONG_ANSWERS + CITY_WRONG_ANSWERS + PERSON_WRONG_ANSWERS
        all_names = [n for n in all_names if n.lower() != correct_answer.lower()]
        wrong = random.sample(all_names, min(3, len(all_names)))
    
    while len(wrong) < 3:
        wrong.append(random.choice(['Неизвестно', 'Нет ответа', 'Вариант Б']))
    
    return [w[:64] for w in wrong[:3]]

def fix_all_questions(database_path: str = "quiz_bot.db"):
    """Исправление всех вопросов."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Получить ВСЕ вопросы
    cursor.execute("SELECT id, text, correct_answer, category FROM questions")
    questions = cursor.fetchall()
    
    print(f"Найдено {len(questions)} вопросов для обработки")
    
    updated = 0
    errors = 0
    
    for i, (q_id, text, correct, category) in enumerate(questions, 1):
        try:
            # Сгенерировать неправильные ответы
            wrong = generate_wrong_answers(correct, text, category or 'GENERAL')
            
            # Обновить в БД
            cursor.execute(
                "UPDATE questions SET wrong_answers = ? WHERE id = ?",
                (json.dumps(wrong, ensure_ascii=False), q_id)
            )
            updated += 1
            
            # Прогресс каждые 100
            if i % 100 == 0:
                print(f"  Обработано {i}/{len(questions)}...")
                conn.commit()  # Промежуточный коммит
                
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  Ошибка: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nOK Исправлено: {updated} вопросов")
    print(f"Ошибок: {errors}")

if __name__ == "__main__":
    print("Запуск исправления всех вопросов...")
    fix_all_questions()
    print("\nOK Готово!")
