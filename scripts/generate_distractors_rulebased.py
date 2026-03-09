"""
Генерация неправильных ответов на основе категори-специфичных словарей.
Покрытие: ~60% вопросов (1,692 из 2,820)
"""
import sqlite3
import json
import random
import re
from pathlib import Path
from typing import List, Dict, Optional

# === СЛОВАРИ ПО КАТЕГОРИЯМ ===
CATEGORY_DICTIONARIES = {
    'GEOGRAPHY': {
        'cities': ['Париж', 'Лондон', 'Берлин', 'Мадрид', 'Рим', 'Вена', 'Прага', 'Варшава', 'Будапешт', 'Амстердам', 'Москва', 'Санкт-Петербург', 'Киев', 'Минск'],
        'countries': ['Франция', 'Германия', 'Италия', 'Испания', 'Польша', 'Чехия', 'Венгрия', 'Австрия', 'Нидерланды', 'Россия', 'Украина', 'Беларусь'],
        'rivers': ['Нил', 'Янцзы', 'Миссисипи', 'Волга', 'Дунай', 'Темза', 'Сена', 'Рейн', 'По'],
    },
    'HISTORY': {
        'years': ['1914', '1939', '1945', '1917', '1812', '1700', '1800', '1900', '1953', '1961', '1964', '1985', '1991'],
        'names': ['Петр I', 'Екатерина II', 'Николай II', 'Александр I', 'Ленин', 'Сталин', 'Хрущев', 'Брежнев', 'Горбачев', 'Иван Грозный'],
    },
    'LITERATURE': {
        'authors': ['Пушкин', 'Толстой', 'Достоевский', 'Чехов', 'Лермонтов', 'Гоголь', 'Тургенев', 'Горький', 'Некрасов', 'Блок'],
        'works': ['Война и мир', 'Преступление и наказание', 'Анна Каренина', 'Евгений Онегин', 'Герой нашего времени', 'Мертвые души'],
    },
    'SCIENCE': {
        'elements': ['Кислород', 'Водород', 'Углерод', 'Азот', 'Железо', 'Медь', 'Золото', 'Серебро', 'Алюминий', 'Кальций'],
        'units': ['метр', 'килограмм', 'секунда', 'ампер', 'кельвин', 'моль', 'ньютон', 'джоуль', 'ватт'],
    },
    'ART': {
        'artists': ['Репин', 'Суриков', 'Шишкин', 'Айвазовский', 'Кустодиев', 'Васнецов', 'Брюллов', 'Левитан'],
        'composers': ['Чайковский', 'Рахманинов', 'Стравинский', 'Прокофьев', 'Мусоргский', 'Глинка', 'Бородин'],
    },
    'SPORT': {
        'teams': ['Спартак', 'ЦСКА', 'Зенит', 'Локомотив', 'Динамо', 'Краснодар', 'Ростов'],
        'sports': ['футбол', 'хоккей', 'баскетбол', 'теннис', 'волейбол', 'плавание', 'легкая атлетика'],
    },
}


def classify_answer_type(correct_answer: str, question_text: str, category: str) -> str:
    """
    Классификация типа правильного ответа.
    Возвращает: 'year', 'city', 'country', 'person', 'river', 'author', 'work', etc.
    """
    answer = correct_answer.strip()
    question_lower = question_text.lower()
    
    # Год (4 цифры)
    if re.match(r'^\d{4}$', answer):
        return 'year'
    
    # Река (ключевые слова в вопросе)
    if any(kw in question_lower for kw in ['река', 'течёт', 'впадает', 'приток']):
        return 'river'
    
    # Город (ключевые слова в вопросе)
    if any(kw in question_lower for kw in ['город', 'столица', 'расположен']):
        return 'city'
    
    # Страна (ключевые слова в вопросе)
    if any(kw in question_lower for kw in ['страна', 'государство', 'держав']):
        return 'country'
    
    # Автор/писатель
    if any(kw in question_lower for kw in ['писатель', 'автор', 'поэт', 'написал', 'создал']):
        return 'author'
    
    # Произведение
    if any(kw in question_lower for kw in ['роман', 'книга', 'произведение', 'повесть', 'рассказ']):
        return 'work'
    
    # Учёный
    if any(kw in question_lower for kw in ['учёный', 'открыл', 'изобрёл', 'физик', 'химик']):
        return 'scientist'
    
    # Художник/композитор
    if any(kw in question_lower for kw in ['художник', 'картина', 'композитор', 'музыка', 'написал симфонию']):
        return 'artist'
    
    # Спортсмен/команда
    if any(kw in question_lower for kw in ['спорт', 'команда', 'игрок', 'чемпион']):
        return 'athlete'
    
    # По умолчанию
    return 'general'


def generate_distractors_rulebased(
    correct_answer: str,
    question_text: str,
    category: str,
    answer_type: str
) -> List[str]:
    """
    Генерация 3 неправильных ответов на основе правил.
    """
    wrong = []
    
    # Стратегия 1: Годы — вариации ±5, ±10, ±25 лет
    if answer_type == 'year':
        try:
            year = int(correct_answer)
            variations = [year-5, year+5, year-10, year+10, year-25, year+25]
            variations = [str(y) for y in variations if 1000 <= y <= 2024]
            if len(variations) >= 3:
                return random.sample(variations, 3)
        except:
            pass
    
    # Стратегия 2: Поиск в словарях по категории
    if category in CATEGORY_DICTIONARIES:
        cat_dict = CATEGORY_DICTIONARIES[category]
        
        # Поиск по типу ответа
        if answer_type in cat_dict:
            pool = cat_dict[answer_type]
            candidates = [x for x in pool if x.lower() != correct_answer.lower()]
            if len(candidates) >= 3:
                return random.sample(candidates, 3)
        
        # Поиск по всем пулам категории
        all_pool = []
        for pool_name, pool_values in cat_dict.items():
            all_pool.extend(pool_values)
        
        candidates = [x for x in all_pool if x.lower() != correct_answer.lower()]
        if len(candidates) >= 3:
            return random.sample(candidates, 3)
    
    # Стратегия 3: Fallback — общие варианты
    fallback = [
        f"Не {correct_answer}",
        "Другой вариант",
        "Альтернативный ответ"
    ]
    return fallback[:3]


def generate_for_database(database_path: str = "quiz_bot.db", limit: int = None):
    """Генерация для всех вопросов в БД."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Найти вопросы с заглушками
    query = """
    SELECT id, text, correct_answer, category, wrong_answers
    FROM questions
    WHERE wrong_answers LIKE '%Вариант%'
    OR wrong_answers LIKE '%вариант%'
    """
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    questions = cursor.fetchall()
    
    print(f"Найдено {len(questions)} вопросов для генерации")
    
    stats = {'generated': 0, 'skipped': 0, 'errors': 0}
    
    for i, (q_id, text, correct, category, current) in enumerate(questions, 1):
        try:
            # Классифицировать тип ответа
            answer_type = classify_answer_type(correct, text, category)
            
            # Сгенерировать неправильные ответы
            wrong = generate_distractors_rulebased(correct, text, category, answer_type)
            
            # Проверка качества
            if len(wrong) < 3 or any('Вариант' in w for w in wrong):
                stats['skipped'] += 1
                continue
            
            # Обновить в БД
            cursor.execute(
                "UPDATE questions SET wrong_answers = ? WHERE id = ?",
                (json.dumps(wrong, ensure_ascii=False), q_id)
            )
            stats['generated'] += 1
            
            if i % 100 == 0:
                print(f"  Обработано {i}/{len(questions)} вопросов...")
                conn.commit()
                
        except Exception as e:
            print(f"  Ошибка для вопроса {q_id}: {e}")
            stats['errors'] += 1
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\nСтатистика:")
    print(f"   Сгенерировано: {stats['generated']}")
    print(f"   Пропущено: {stats['skipped']}")
    print(f"   Ошибок: {stats['errors']}")
    total = stats['generated'] + stats['skipped'] + stats['errors']
    if total > 0:
        print(f"   Успешность: {stats['generated']/total*100:.1f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Ограничить количество (для теста)')
    parser.add_argument('--db', default='quiz_bot.db', help='Путь к БД')
    args = parser.parse_args()
    
    print("Запуск генерации неправильных ответов (rule-based)...")
    generate_for_database(args.db, args.limit)
    print("\nГотово!")
