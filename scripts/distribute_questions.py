#!/usr/bin/env python3
"""
Распределение вопросов по категориям на основе ключевых слов.
Использует прямой SQL для надёжности с SQLite.
"""

import sqlite3
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Категории и ключевые слова (расширенный список)
CATEGORY_KEYWORDS = {
    'SCIENCE': [
        'наука', 'физика', 'химия', 'биология', 'космос', 'планета', 'звезда', 'галактика',
        'атом', 'молекула', 'элемент', 'реакция', 'ген', 'днк', 'клетка', 'организм',
        'математика', 'формула', 'уравнение', 'теорема', 'закон', 'теория',
        'исследование', 'эксперимент', 'открытие', 'учёный', 'академия'
    ],
    'HISTORY': [
        'история', 'война', 'битва', 'сражение', 'царь', 'император', 'король', 'королева',
        'революция', 'восстание', 'переворот', 'древний', 'век', 'эпоха', 'период',
        'средневековье', 'античность', 'рим', 'греция', 'египет', 'викинг',
        'президент', 'политик', 'правитель', 'лидер', 'государство', 'империя'
    ],
    'GEOGRAPHY': [
        'город', 'страна', 'река', 'море', 'океан', 'озеро', 'гора', 'пустыня',
        'остров', 'полуостров', 'континент', 'материк', 'штат', 'провинция',
        'столица', 'регион', 'местность', 'территория', 'граница', 'география',
        'климат', 'погода', 'широта', 'долгота', 'экватор', 'полюс'
    ],
    'ART': [
        'художник', 'картина', 'живопись', 'рисунок', 'музей', 'галерея',
        'музыка', 'композитор', 'песня', 'опера', 'симфония', 'оркестр',
        'писатель', 'книга', 'роман', 'поэзия', 'стихи', 'литература',
        'актер', 'театр', 'кино', 'фильм', 'режиссёр', 'сценарий',
        'скульптура', 'архитектура', 'здание', 'памятник', 'творчество'
    ],
    'SPORT': [
        'спорт', 'футбол', 'хоккей', 'баскетбол', 'волейбол', 'теннис',
        'олимпиада', 'олимпийский', 'чемпион', 'чемпионат', 'турнир', 'кубок',
        'атлет', 'спортсмен', 'тренер', 'команда', 'матч', 'игра', 'соревнование',
        'рекорд', 'медаль', 'победа', 'поражение', 'финал', 'полуфинал'
    ],
    'NATURE': [
        'природа', 'животное', 'растение', 'птица', 'рыба', 'насекомое',
        'дерево', 'цветок', 'трава', 'лес', 'джунгли', 'саванна', 'тундра',
        'погода', 'дождь', 'снег', 'ветер', 'гроза', 'ураган', 'засуха',
        'экология', 'окружающая среда', 'заповедник', 'национальный парк'
    ],
    'TECHNOLOGY': [
        'технология', 'компьютер', 'интернет', 'телефон', 'смартфон', 'приложение',
        'робот', 'автоматизация', 'искусственный интеллект', 'нейросеть', 'алгоритм',
        'программа', 'программирование', 'код', 'сайт', 'база данных', 'сервер',
        'электроника', 'чип', 'процессор', 'гаджет', 'устройство', 'механизм'
    ],
}

# Ключевые слова для определения сложности
DIFFICULTY_KEYWORDS = {
    'EASY': [
        'простой', 'легкий', 'основной', 'базовый', 'известный', 'известно',
        'общий', 'стандартный', 'типичный', 'обычный', 'распространённый'
    ],
    'HARD': [
        'сложный', 'трудный', 'сложно', 'трудно', 'редкий', 'неизвестный',
        'специальный', 'профессиональный', 'технический', 'научный',
        'детальный', 'подробный', 'глубокий', 'секретный', 'закрытый'
    ],
}


def distribute_categories():
    """Распределить вопросы по категориям."""
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    
    total_updated = 0
    
    print("=== РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ ===\n")
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        category_updated = 0
        
        for keyword in keywords:
            # Используем LOWER() для case-insensitive поиска
            cursor.execute("""
                UPDATE questions 
                SET category = ?
                WHERE LOWER(text) LIKE ?
                AND category = 'GENERAL'
            """, (category, f'%{keyword.lower()}%'))
            
            updated = cursor.rowcount
            if updated > 0:
                print(f"  {keyword} -> {category}: {updated}")
                category_updated += updated
        
        if category_updated > 0:
            conn.commit()  # Коммит после каждой категории
            print(f"OK {category}: всего {category_updated} вопросов\n")
            total_updated += category_updated
    
    print(f"=== ВСЕГО ОБНОВЛЕНО: {total_updated} вопросов ===\n")
    
    conn.close()
    return total_updated


def distribute_difficulty():
    """Распределить вопросы по сложности."""
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    
    total_updated = 0
    
    print("=== РАСПРЕДЕЛЕНИЕ ПО СЛОЖНОСТИ ===\n")
    
    # Сначала помечаем EASY вопросы
    easy_updated = 0
    for keyword in DIFFICULTY_KEYWORDS['EASY']:
        cursor.execute("""
            UPDATE questions 
            SET difficulty = 'EASY'
            WHERE LOWER(text) LIKE ?
            AND difficulty = 'MEDIUM'
        """, (f'%{keyword.lower()}%',))
        
        updated = cursor.rowcount
        if updated > 0:
            print(f"  {keyword} -> EASY: {updated}")
            easy_updated += updated
    
    if easy_updated > 0:
        conn.commit()
        print(f"OK EASY: всего {easy_updated} вопросов\n")
        total_updated += easy_updated
    
    # Затем помечаем HARD вопросы
    hard_updated = 0
    for keyword in DIFFICULTY_KEYWORDS['HARD']:
        cursor.execute("""
            UPDATE questions 
            SET difficulty = 'HARD'
            WHERE LOWER(text) LIKE ?
            AND difficulty = 'MEDIUM'
        """, (f'%{keyword.lower()}%',))
        
        updated = cursor.rowcount
        if updated > 0:
            print(f"  {keyword} -> HARD: {updated}")
            hard_updated += updated
    
    if hard_updated > 0:
        conn.commit()
        print(f"OK HARD: всего {hard_updated} вопросов\n")
        total_updated += hard_updated
    
    print(f"=== ВСЕГО ОБНОВЛЕНО: {total_updated} вопросов ===\n")
    
    conn.close()
    return total_updated


def show_statistics():
    """Показать статистику распределения."""
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    
    print("=== ИТОГОВАЯ СТАТИСТИКА ===\n")
    
    print("Категории:")
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM questions 
        GROUP BY category 
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\nСложность:")
    cursor.execute("""
        SELECT difficulty, COUNT(*) as count 
        FROM questions 
        GROUP BY difficulty 
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    total = cursor.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    general_count = cursor.execute(
        "SELECT COUNT(*) FROM questions WHERE category = 'GENERAL'"
    ).fetchone()[0]
    
    print(f"\nOK Всего вопросов: {total}")
    print(f"WARNING GENERAL: {general_count} ({general_count/total*100:.1f}%)")
    
    conn.close()


if __name__ == "__main__":
    print("Начинаем распределение вопросов...\n")
    
    # Распределяем по категориям
    cat_updated = distribute_categories()
    
    # Распределяем по сложности
    diff_updated = distribute_difficulty()
    
    # Показываем статистику
    show_statistics()
    
    print(f"\n{'='*50}")
    print("OK Распределение завершено!")
    print(f"   Обновлено категорий: {cat_updated}")
    print(f"   Обновлено сложности: {diff_updated}")
    print(f"{'='*50}")
