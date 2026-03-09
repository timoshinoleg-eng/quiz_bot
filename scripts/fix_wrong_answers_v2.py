#!/usr/bin/env python3
"""
Улучшенная генерация неправильных ответов на основе категории вопроса.
Использует тематические словари для генерации правдоподобных вариантов.
"""

import sqlite3
import json
import random
import re
from pathlib import Path
import sys

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# === БАЗЫ ПРАВДОПОДОБНЫХ НЕПРАВИЛЬНЫХ ОТВЕТОВ ===

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

ART_WORKS = ['Мона Лиза', 'Звёздная ночь', 'Герника', 'Девятая волна', 'Богатыри']

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
        'wrong_pool': PERSON_WRONG_ANSWERS + ART_WORKS
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

def generate_plausible_wrong_answers(correct_answer: str, question_text: str, category: str) -> list:
    """
    Генерация правдоподобных неправильных ответов.
    """
    wrong = []
    
    # Определить категорию если GENERAL
    if category == 'GENERAL':
        category = get_category_from_question(question_text)
    
    # Стратегия 1: Использовать пул категории
    if category in CATEGORY_MAP:
        pool = CATEGORY_MAP[category]['wrong_pool'][:]
        # Исключить правильный ответ из пула
        pool = [a for a in pool if a.lower() != correct_answer.lower()]
        if len(pool) >= 3:
            wrong = random.sample(pool, 3)
            return wrong
    
    # Стратегия 2: Если ответ содержит число/год (4 цифры)
    numbers = re.findall(r'\d{4}', correct_answer)
    if numbers and not wrong:
        year = int(numbers[0])
        wrong = [str(year - 1), str(year + 1), str(year - 5)]
        return wrong
    
    # Стратегия 3: Если ответ содержит число
    numbers = re.findall(r'\d+', correct_answer)
    if numbers and not wrong:
        num = int(numbers[0])
        wrong = [str(num - 1), str(num + 1), str(num + 10)]
        # Если в ответе есть текст + число
        if len(correct_answer) > len(str(num)):
            wrong = [correct_answer.replace(str(num), w) for w in wrong]
        return wrong
    
    # Стратегия 4: Если ответ содержит имя собственное (заглавная буква)
    if correct_answer and correct_answer[0].isupper() and len(correct_answer) > 3:
        # Собрать все имена из всех пулов
        all_names = []
        for pools in CATEGORY_MAP.values():
            for values in pools['wrong_pool']:
                all_names.append(values)
        
        all_names = [n for n in all_names if n.lower() != correct_answer.lower()]
        if len(all_names) >= 3:
            wrong = random.sample(all_names, 3)
            return wrong
    
    # Стратегия 5: Fallback для GENERAL
    if not wrong:
        generic_pool = [
            'США', 'Китай', 'Индия', 'Бразилия', 'Россия',
            'Париж', 'Лондон', 'Токио', 'Пекин', 'Москва',
            'Эйнштейн', 'Ньютон', 'Дарвин', 'Пушкин', 'Толстой'
        ]
        generic_pool = [a for a in generic_pool if a.lower() != correct_answer.lower()]
        wrong = random.sample(generic_pool, min(3, len(generic_pool)))
    
    # Дозаполнить если меньше 3
    while len(wrong) < 3:
        wrong.append(random.choice(['Вариант А', 'Вариант Б', 'Вариант В']))
    
    # Обрезать до 64 символов (лимит MAX API)
    return [w[:64] for w in wrong[:3]]

def fix_database(database_path: str = "quiz_bot.db", limit: int = None):
    """Исправление неправильных ответов в БД."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Найти вопросы (обрабатываем все, у которых wrong_answers выглядит как заглушка)
    # Проверяем по длине - заглушки короткие
    cursor.execute("""
        SELECT id, text, correct_answer, wrong_answers, category
        FROM questions
        WHERE LENGTH(wrong_answers) < 100  -- Заглушки короткие
    """)
    
    all_questions = cursor.fetchall()
    
    # Фильтруем только те, что содержат заглушки
    questions = []
    for q in all_questions:
        wrong = q[3]  # wrong_answers column
        if wrong and ('Вариант' in wrong or 'вариант' in wrong or wrong == '[]' or wrong is None):
            questions.append(q)
    
    if limit:
        questions = questions[:limit]
    
    print(f"Найдено {len(questions)} вопросов для исправления")
    
    updated = 0
    errors = 0
    
    for i, (q_id, text, correct, current, category) in enumerate(questions, 1):
        try:
            # Сгенерировать неправильные ответы
            wrong = generate_plausible_wrong_answers(correct, text, category or 'GENERAL')
            
            # Обновить в БД
            cursor.execute(
                "UPDATE questions SET wrong_answers = ? WHERE id = ?",
                (json.dumps(wrong, ensure_ascii=False), q_id)
            )
            updated += 1
            
            # Прогресс каждые 100 вопросов
            if i % 100 == 0:
                print(f"  Обработано {i}/{len(questions)} вопросов...")
                
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Ошибка для вопроса {q_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nOK Исправлено: {updated} вопросов")
    print(f"Ошибок: {errors}")
    if updated + errors > 0:
        print(f"Успешность: {updated/(updated+errors)*100:.1f}%")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Исправление неправильных ответов')
    parser.add_argument('--limit', type=int, help='Ограничить количество вопросов (для теста)')
    parser.add_argument('--db', default='quiz_bot.db', help='Путь к базе данных')
    
    args = parser.parse_args()
    
    print("Запуск исправления неправильных ответов...")
    fix_database(args.db, args.limit)
    print("\nOK Готово!")
