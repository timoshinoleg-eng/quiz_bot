"""Загрузка вопросов из Open Trivia Database API."""
import requests
import json
import time
from pathlib import Path


def fetch_questions(amount=50, category=None, difficulty=None, question_type='multiple'):
    """Загрузка вопросов из OpenTDB."""
    base_url = 'https://opentdb.com/api.php'
    
    params = {
        'amount': amount,
        'type': question_type  # multiple для MCQ
    }
    
    if category:
        params['category'] = category
    if difficulty:
        params['difficulty'] = difficulty
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data['response_code'] == 0:
            return data['results']
    
    return []


def get_all_categories():
    """Получение списка категорий."""
    response = requests.get('https://opentdb.com/api_category.php')
    if response.status_code == 200:
        return response.json()['trivia_categories']
    return []


def convert_to_ru_format(questions):
    """Конвертация вопросов OpenTDB в формат MAX-Квиз."""
    converted = []
    
    # Маппинг категорий
    category_map = {
        'General Knowledge': 'GENERAL',
        'Entertainment: Books': 'ART',
        'Entertainment: Film': 'ART',
        'Entertainment: Music': 'ART',
        'Entertainment: Musicals & Theatres': 'ART',
        'Entertainment: Television': 'ART',
        'Entertainment: Video Games': 'GENERAL',
        'Entertainment: Board Games': 'GENERAL',
        'Science & Nature': 'SCIENCE',
        'Science: Computers': 'SCIENCE',
        'Science: Mathematics': 'SCIENCE',
        'Mythology': 'HISTORY',
        'Sports': 'SPORT',
        'Geography': 'GEOGRAPHY',
        'History': 'HISTORY',
        'Politics': 'GENERAL',
        'Art': 'ART',
        'Celebrities': 'GENERAL',
        'Animals': 'NATURE',
        'Vehicles': 'TECHNOLOGY',
        'Entertainment: Comics': 'ART',
        'Science: Gadgets': 'TECHNOLOGY',
        'Entertainment: Japanese Anime & Manga': 'ART',
        'Entertainment: Cartoon & Animations': 'ART'
    }
    
    for q in questions:
        converted.append({
            'text': q['question'],
            'correct_answer': q['correct_answer'],
            'wrong_answers': q['incorrect_answers'],
            'category': category_map.get(q['category'], 'GENERAL'),
            'difficulty': q['difficulty'].upper(),
            'source': 'OpenTDB',
            'original_category': q['category']
        })
    
    return converted


def main():
    """Основная функция загрузки."""
    print("=" * 60)
    print("Загрузка вопросов из Open Trivia Database")
    print("=" * 60)
    
    # Получаем категории
    categories = get_all_categories()
    print(f"\nНайдено {len(categories)} категорий")
    
    all_questions = []
    
    # Загружаем вопросы по каждой категории
    for cat in categories:
        print(f"\nЗагрузка категории: {cat['name']} (ID: {cat['id']})")
        
        # Загружаем по 50 вопросов разной сложности
        for difficulty in ['easy', 'medium', 'hard']:
            questions = fetch_questions(
                amount=50,
                category=cat['id'],
                difficulty=difficulty
            )
            
            if questions:
                print(f"  {difficulty}: {len(questions)} вопросов")
                all_questions.extend(questions)
            
            # Задержка чтобы не перегружать API
            time.sleep(0.5)
    
    print(f"\nВсего загружено: {len(all_questions)} вопросов")
    
    # Конвертируем в формат MAX-Квиз
    converted = convert_to_ru_format(all_questions)
    
    # Сохраняем
    output_dir = Path('data/generated')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'opentdb_questions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
    
    print(f"\nСохранено в: {output_file}")
    
    # Статистика
    from collections import Counter
    categories_count = Counter(q['category'] for q in converted)
    difficulties_count = Counter(q['difficulty'] for q in converted)
    
    print("\nПо категориям:")
    for cat, count in categories_count.most_common():
        print(f"  {cat}: {count}")
    
    print("\nПо сложности:")
    for diff, count in difficulties_count.most_common():
        print(f"  {diff}: {count}")


if __name__ == "__main__":
    main()
