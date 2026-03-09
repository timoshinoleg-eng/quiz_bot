"""Генерация вопросов из словарей данных."""
import pandas as pd
import random
import json
from typing import List, Dict
from pathlib import Path


class DictionaryQuestionGenerator:
    """Генератор вопросов на основе словарей."""
    
    def __init__(self, dictionaries_path: str = "data/dictionaries"):
        self.dictionaries_path = Path(dictionaries_path)
        self.data = {}
        self._load_data()
    
    def _load_data(self):
        """Загружает все словари."""
        # Russian Cities
        cities_path = self.dictionaries_path / "russian_cities.csv"
        if cities_path.exists():
            self.data['cities'] = pd.read_csv(cities_path)
            print(f"Loaded {len(self.data['cities'])} cities")
        
        # Russian Literature
        lit_path = self.dictionaries_path / "russian_literature" / "russian_literature.csv"
        if lit_path.exists():
            self.data['literature'] = pd.read_csv(lit_path)
            print(f"Loaded {len(self.data['literature'])} literary works")
        
        # Russian Historical Events
        hist_path = self.dictionaries_path / "histolines" / "events" / "russian_historical_events.csv"
        if hist_path.exists():
            self.data['history'] = pd.read_csv(hist_path)
            print(f"Loaded {len(self.data['history'])} historical events")
    
    def generate_geography_questions(self, count: int = 20) -> List[Dict]:
        """Генерирует вопросы по географии."""
        questions = []
        
        if 'cities' not in self.data:
            return questions
        
        cities = self.data['cities']
        
        # 1. Вопросы о столицах регионов
        capitals = cities[cities['capital'] == 'admin']
        for _, row in capitals.sample(min(count // 3, len(capitals))).iterrows():
            region = row['admin_name']
            city = row['city']
            
            # Получаем неправильные ответы
            wrong_cities = cities[cities['city'] != city]['city'].sample(3).tolist()
            
            questions.append({
                'text': f'Какой город является административным центром {region}?',
                'correct_answer': city,
                'wrong_answers': wrong_cities,
                'category': 'GEOGRAPHY',
                'difficulty': 'MEDIUM'
            })
        
        # 2. Вопросы о крупнейших городах
        largest = cities.nlargest(50, 'population')
        for _, row in largest.sample(min(count // 3, len(largest))).iterrows():
            city = row['city']
            region = row['admin_name']
            
            wrong_cities = cities[cities['city'] != city]['city'].sample(3).tolist()
            
            questions.append({
                'text': f'В каком регионе находится город {city}?',
                'correct_answer': region,
                'wrong_answers': wrong_cities,
                'category': 'GEOGRAPHY',
                'difficulty': 'EASY' if row['population'] > 1000000 else 'MEDIUM'
            })
        
        # 3. Вопросы о населении
        largest = cities.nlargest(30, 'population')
        for _, row in largest.sample(min(count // 3, len(largest))).iterrows():
            city = row['city']
            pop = int(row['population'])
            
            # Генерируем варианты с округлением
            correct = round(pop, -5)
            wrong = [
                round(pop * 0.7, -5),
                round(pop * 1.3, -5),
                round(pop * 0.5, -5)
            ]
            
            questions.append({
                'text': f'Каково примерное население города {city}?',
                'correct_answer': f"~{int(correct):,}".replace(',', ' '),
                'wrong_answers': [f"~{int(w):,}".replace(',', ' ') for w in wrong],
                'category': 'GEOGRAPHY',
                'difficulty': 'HARD'
            })
        
        return questions[:count]
    
    def generate_literature_questions(self, count: int = 20) -> List[Dict]:
        """Генерирует вопросы по литературе."""
        questions = []
        
        if 'literature' not in self.data:
            return questions
        
        lit = self.data['literature']
        
        # 1. Автор произведения
        for _, row in lit.sample(min(count // 2, len(lit))).iterrows():
            title = row['title']
            author = row['author']
            
            # Получаем других авторов
            wrong_authors = lit[lit['author'] != author]['author'].unique()
            wrong = random.sample(list(wrong_authors), min(3, len(wrong_authors)))
            
            questions.append({
                'text': f'Кто написал произведение "{title}"?',
                'correct_answer': author,
                'wrong_answers': wrong,
                'category': 'ART',
                'difficulty': 'MEDIUM'
            })
        
        # 2. Год публикации
        for _, row in lit.sample(min(count // 2, len(lit))).iterrows():
            title = row['title']
            year = int(row['year'])
            
            # Генерируем варианты
            offsets = random.sample([-30, -15, -5, 5, 15, 30], 3)
            wrong = [str(year + o) for o in offsets]
            
            questions.append({
                'text': f'В каком году было опубликовано произведение "{title}"?',
                'correct_answer': str(year),
                'wrong_answers': wrong,
                'category': 'ART',
                'difficulty': 'HARD'
            })
        
        return questions[:count]
    
    def generate_history_questions(self, count: int = 20) -> List[Dict]:
        """Генерирует вопросы по истории."""
        questions = []
        
        if 'history' not in self.data:
            return questions
        
        hist = self.data['history']
        
        # Фильтруем значимые события (не "took a picture")
        significant = hist[~hist['whatEventType'].isin(['took a picture'])]
        
        # 1. Год рождения/смерти
        for event_type in ['was born', 'died']:
            events = significant[significant['whatEventType'] == event_type]
            if len(events) == 0:
                continue
                
            for _, row in events.sample(min(count // 4, len(events))).iterrows():
                person = row['whoCharName']
                year = int(row['whenYear'])
                
                if year == 0:
                    continue
                
                # Определяем текст вопроса
                action = "родился" if event_type == 'was born' else "умер"
                
                # Генерируем варианты
                offsets = random.sample([-20, -10, -5, 5, 10, 20], 3)
                wrong = [str(year + o) for o in offsets]
                
                questions.append({
                    'text': f'В каком году {action} {person}?',
                    'correct_answer': str(year),
                    'wrong_answers': wrong,
                    'category': 'HISTORY',
                    'difficulty': 'MEDIUM'
                })
        
        # 2. Прочие события
        other_events = significant[
            significant['whatEventType'].isin(['got a job as', 'lost a job as', 'became', 'received'])
        ]
        
        for _, row in other_events.sample(min(count // 4, len(other_events))).iterrows():
            person = row['whoCharName']
            event = row['whatEventType']
            year = int(row['whenYear'])
            detail = row['eventDetail'] if pd.notna(row['eventDetail']) else ''
            
            if year == 0:
                continue
            
            # Переводим событие
            event_translations = {
                'got a job as': 'получил должность',
                'lost a job as': 'потерял должность',
                'became': 'стал',
                'received': 'получил'
            }
            
            event_ru = event_translations.get(event, event)
            
            offsets = random.sample([-10, -5, -2, 2, 5, 10], 3)
            wrong = [str(year + o) for o in offsets]
            
            questions.append({
                'text': f'Когда {person} {event_ru}?',
                'correct_answer': str(year),
                'wrong_answers': wrong,
                'category': 'HISTORY',
                'difficulty': 'HARD'
            })
        
        return questions[:count]
    
    def generate_all_questions(self) -> Dict[str, List[Dict]]:
        """Генерирует все вопросы из словарей."""
        return {
            'geography': self.generate_geography_questions(30),
            'literature': self.generate_literature_questions(20),
            'history': self.generate_history_questions(30)
        }
    
    def save_questions_to_json(self, output_path: str = "data/dictionary_questions.json"):
        """Сохраняет вопросы в JSON."""
        questions = self.generate_all_questions()
        
        # Плоский список всех вопросов
        all_questions = []
        for category, qs in questions.items():
            all_questions.extend(qs)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)
        
        print(f"\nTotal questions generated: {len(all_questions)}")
        print(f"Saved to: {output_path}")
        
        # Статистика по категориям
        print("\nBy category:")
        for category, qs in questions.items():
            print(f"  {category}: {len(qs)}")
        
        return all_questions


if __name__ == "__main__":
    print("=" * 60)
    print("Dictionary Question Generator")
    print("=" * 60)
    
    generator = DictionaryQuestionGenerator()
    questions = generator.save_questions_to_json()
    
    # Показываем примеры
    print("\n" + "=" * 60)
    print("Sample Questions:")
    print("=" * 60)
    
    for q in questions[:5]:
        print(f"\n[{q['category']}] {q['difficulty']}")
        print(f"Q: {q['text']}")
        print(f"A: {q['correct_answer']}")
        print(f"Wrong: {', '.join(q['wrong_answers'])}")
