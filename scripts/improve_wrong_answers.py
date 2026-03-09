#!/usr/bin/env python3
"""
Улучшение неправильных ответов - замена заглушек на релевантные варианты.
"""

import sqlite3
import json
import random
import re

# Пулы ответов по категориям (расширенные)
CATEGORY_POOLS = {
    'GEOGRAPHY': {
        'cities': ['Париж', 'Лондон', 'Берлин', 'Мадрид', 'Рим', 'Вена', 'Прага', 'Варшава', 
                   'Амстердам', 'Брюссель', 'Москва', 'Санкт-Петербург', 'Киев', 'Минск', 
                   'Токио', 'Пекин', 'Дели', 'Каир', 'Стамбул', 'Нью-Йорк', 'Лос-Анджелес'],
        'countries': ['Франция', 'Германия', 'Италия', 'Испания', 'Польша', 'Чехия', 
                      'Австрия', 'Великобритания', 'США', 'Канада', 'Австралия', 'Япония',
                      'Китай', 'Индия', 'Россия', 'Бразилия', 'Аргентина', 'Египет', 'Турция'],
        'rivers': ['Нил', 'Амазонка', 'Янцзы', 'Миссисипи', 'Волга', 'Дунай', 'Темза', 'Сена'],
    },
    'HISTORY': {
        'years': ['1492', '1812', '1914', '1917', '1939', '1941', '1945', '1961', '1986', '1991'],
        'rulers': ['Петр I', 'Екатерина II', 'Николай II', 'Александр I', 'Александр II',
                   'Иван Грозный', 'Владимир Ленин', 'Иосиф Сталин', 'Наполеон', 'Гитлер'],
        'battles': ['Бородино', 'Сталинград', 'Курская дуга', 'Ватерлоо', 'Геттисберг'],
    },
    'SCIENCE': {
        'scientists': ['Эйнштейн', 'Ньютон', 'Дарвин', 'Кюри', 'Тесла', 'Галилей', 
                       'Архимед', 'Менделеев', 'Ломоносов', 'Попов'],
        'elements': ['Золото', 'Серебро', 'Железо', 'Медь', 'Алюминий', 'Кислород', 'Азот'],
    },
    'ART': {
        'writers': ['Пушкин', 'Толстой', 'Достоевский', 'Чехов', 'Гоголь', 'Лермонтов',
                    'Тургенев', 'Бунин', 'Пастернак', 'Булгаков'],
        'artists': ['Репин', 'Левитан', 'Васнецов', 'Шишкин', 'Айвазовский'],
        'composers': ['Чайковский', 'Моцарт', 'Бетховен', 'Бах', 'Вивальди'],
    },
    'SPORT': {
        'teams': ['Спартак', 'ЦСКА', 'Зенит', 'Локомотив', 'Динамо', 'Краснодар',
                  'Барселона', 'Реал Мадрид', 'Манчестер', 'Ливерпуль', 'Ювентус'],
        'athletes': ['Месси', 'Роналду', 'Овечкин', 'Малкин', 'Шарапова', 'Кабаева',
                     'Карякин', 'Непомнящий'],
    },
}

ALL_CITIES = ['Париж', 'Лондон', 'Берлин', 'Мадрид', 'Рим', 'Москва', 'Токио', 'Пекин', 'Нью-Йорк']
ALL_COUNTRIES = ['Франция', 'Германия', 'Италия', 'Испания', 'Россия', 'США', 'Китай', 'Бразилия']
ALL_NAMES = ['Эйнштейн', 'Ньютон', 'Пушкин', 'Толстой', 'Моцарт', 'Бетховен', 'Наполеон', 'Цезарь']

def is_place(answer):
    """Проверка - является ли ответ местом (город/страна)."""
    return answer in ALL_CITIES or answer in ALL_COUNTRIES

def is_year(answer):
    """Проверка - является ли ответ годом."""
    return bool(re.match(r'^\d{4}$', answer))

def is_person(answer):
    """Проверка - является ли ответ именем человека."""
    return answer in ALL_NAMES or len(answer.split()) >= 2

def get_wrong_answers_improved(correct_answer: str, question_text: str, category: str) -> list:
    """Улучшенная генерация неправильных ответов."""
    
    wrong = []
    
    # Стратегия 1: Если ответ - год
    if is_year(correct_answer):
        year = int(correct_answer)
        wrong = [str(year - 1), str(year + 1), str(year - 10)]
        return wrong
    
    # Стратегия 2: Если ответ - город/страна
    if is_place(correct_answer):
        if correct_answer in ALL_CITIES:
            pool = [c for c in ALL_CITIES if c != correct_answer]
        else:
            pool = [c for c in ALL_COUNTRIES if c != correct_answer]
        
        if len(pool) >= 3:
            wrong = random.sample(pool, 3)
            return wrong
    
    # Стратегия 3: Если ответ - имя человека
    if is_person(correct_answer):
        pool = [n for n in ALL_NAMES if n != correct_answer]
        if len(pool) >= 3:
            wrong = random.sample(pool, 3)
            return wrong
    
    # Стратегия 4: По категории из пулов
    if category in CATEGORY_POOLS:
        # Выбираем случайный под-пул
        sub_pools = list(CATEGORY_POOLS[category].values())
        all_in_category = []
        for pool in sub_pools:
            all_in_category.extend(pool)
        
        all_in_category = [a for a in all_in_category if a != correct_answer]
        if len(all_in_category) >= 3:
            wrong = random.sample(all_in_category, 3)
            return wrong
    
    # Стратегия 5: Fallback - вариации правильного ответа
    if len(correct_answer) > 3:
        wrong = [
            f"Не {correct_answer}",
            f"Другой вариант",
            f"Альтернатива"
        ]
    else:
        wrong = ["Вариант А", "Вариант Б", "Вариант В"]
    
    return wrong

def improve_wrong_answers(database_path: str = "quiz_bot.db"):
    """Улучшение неправильных ответов в БД."""
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Найти вопросы с плохими ответами
    cursor.execute("""
        SELECT id, text, correct_answer, wrong_answers, category
        FROM questions
        WHERE wrong_answers LIKE '%Вариант%' 
           OR wrong_answers LIKE '%Неверный%'
           OR wrong_answers LIKE '%Альтернатива%'
           OR wrong_answers LIKE '%Другой вариант%'
    """)
    
    questions = cursor.fetchall()
    print(f"Найдено {len(questions)} вопросов с плохими ответами")
    
    updated = 0
    
    for q_id, text, correct, current, category in questions:
        try:
            # Получить улучшенные ответы
            wrong = get_wrong_answers_improved(correct, text, category)
            
            # Обновить
            cursor.execute(
                "UPDATE questions SET wrong_answers = ? WHERE id = ?",
                (json.dumps(wrong, ensure_ascii=False), q_id)
            )
            updated += 1
            
            if updated % 100 == 0:
                print(f"  Обновлено {updated}...")
                
        except Exception as e:
            print(f"  Ошибка: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nOK Улучшено: {updated} вопросов")

if __name__ == "__main__":
    improve_wrong_answers()
