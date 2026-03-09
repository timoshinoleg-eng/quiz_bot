"""Обработка и генерация вопросов из Kaggle датасетов."""
import pandas as pd
import json
import random
from pathlib import Path
from typing import List, Dict


class KaggleDataProcessor:
    """Обработчик данных из Kaggle."""
    
    def __init__(self, base_path: str = "data/dictionaries"):
        self.base_path = Path(base_path)
        self.questions = []
    
    def process_world_population(self) -> List[Dict]:
        """Генерирует вопросы из датасета о населении мира."""
        questions = []
        
        csv_path = self.base_path / "world_population" / "world_population.csv"
        if not csv_path.exists():
            print(f"File not found: {csv_path}")
            return questions
        
        try:
            df = pd.read_csv(csv_path)
            print(f"World Population: {len(df)} countries")
            
            # 1. Вопросы о столицах (если есть колонка Capital)
            if 'Capital' in df.columns:
                for _, row in df.sample(min(20, len(df))).iterrows():
                    country = row['Country/Territory']
                    capital = row['Capital']
                    
                    wrong_capitals = df[df['Capital'] != capital]['Capital'].sample(min(3, len(df)-1)).tolist()
                    
                    questions.append({
                        'text': f"What is the capital of {country}?",
                        'correct_answer': str(capital),
                        'wrong_answers': [str(c) for c in wrong_capitals],
                        'category': 'GEOGRAPHY',
                        'difficulty': 'MEDIUM'
                    })
            
            # 2. Вопросы о населении 2022
            if '2022 Population' in df.columns:
                top_countries = df.nlargest(30, '2022 Population')
                for _, row in top_countries.sample(min(15, len(top_countries))).iterrows():
                    country = row['Country/Territory']
                    pop = int(row['2022 Population'])
                    
                    # Округляем до миллионов
                    correct = round(pop, -6)
                    wrong = [round(pop * random.uniform(0.5, 1.5), -6) for _ in range(3)]
                    
                    questions.append({
                        'text': f"What is the approximate population of {country} (2022)?",
                        'correct_answer': f"~{int(correct/1e6)} million",
                        'wrong_answers': [f"~{int(w/1e6)} million" for w in wrong],
                        'category': 'GEOGRAPHY',
                        'difficulty': 'HARD'
                    })
            
            # 3. Вопросы о росте населения
            if 'Growth Rate' in df.columns:
                fastest = df.nlargest(15, 'Growth Rate')
                for _, row in fastest.iterrows():
                    country = row['Country/Territory']
                    growth = float(row['Growth Rate'])
                    
                    questions.append({
                        'text': f"Which country has a population growth rate of {growth:.2f}%?",
                        'correct_answer': str(country),
                        'wrong_answers': df['Country/Territory'].sample(3).tolist(),
                        'category': 'GEOGRAPHY',
                        'difficulty': 'HARD'
                    })
                    
        except Exception as e:
            print(f"Error processing world_population: {e}")
        
        return questions[:40]  # Ограничиваем количество
    
    def process_russian_literature(self) -> List[Dict]:
        """Генерирует вопросы из датасета о русской литературе."""
        questions = []
        
        base_path = self.base_path / "russian_literature_full"
        if not base_path.exists():
            print(f"Path not found: {base_path}")
            return questions
        
        try:
            # Собираем данные из всех папок
            authors_data = []
            
            prose_path = base_path / "prose"
            if prose_path.exists():
                for author_dir in prose_path.iterdir():
                    if author_dir.is_dir():
                        info_file = author_dir / "info.csv"
                        if info_file.exists():
                            try:
                                df = pd.read_csv(info_file, encoding='utf-8')
                                for _, row in df.iterrows():
                                    authors_data.append({
                                        'author': author_dir.name,
                                        'work': row.get('name', ''),
                                        'year': row.get('year', 0)
                                    })
                            except:
                                pass
            
            print(f"Russian Literature: {len(authors_data)} works found")
            
            # 1. Автор произведения
            if authors_data:
                random.shuffle(authors_data)
                for item in authors_data[:30]:
                    work = item['work']
                    author = item['author']
                    
                    # Получаем других авторов
                    other_authors = list(set([a['author'] for a in authors_data if a['author'] != author]))
                    if len(other_authors) >= 3:
                        wrong = random.sample(other_authors, 3)
                        
                        questions.append({
                            'text': f'Who wrote "{work}"?',
                            'correct_answer': author,
                            'wrong_answers': wrong,
                            'category': 'ART',
                            'difficulty': 'MEDIUM'
                        })
            
            # 2. Год публикации
            year_data = [a for a in authors_data if a['year'] and a['year'] != 0]
            if year_data:
                random.shuffle(year_data)
                for item in year_data[:20]:
                    work = item['work']
                    year = int(item['year']) if isinstance(item['year'], (int, float)) else 1900
                    
                    wrong_years = [str(year + random.randint(-50, 50)) for _ in range(3)]
                    
                    questions.append({
                        'text': f'When was "{work}" published?',
                        'correct_answer': str(year),
                        'wrong_answers': wrong_years,
                        'category': 'ART',
                        'difficulty': 'HARD'
                    })
                    
        except Exception as e:
            print(f"Error processing russian_literature: {e}")
        
        return questions[:50]
    
    def process_movies(self) -> List[Dict]:
        """Генерирует вопросы из датасета о фильмах IMDB."""
        questions = []
        
        csv_path = self.base_path / "imdb_movies" / "imdb_top_movies.csv"
        if not csv_path.exists():
            print(f"File not found: {csv_path}")
            return questions
        
        try:
            df = pd.read_csv(csv_path)
            print(f"Movies: {len(df)} movies")
            
            # 1. Режиссёры топовых фильмов
            top_movies = df.head(50)  # Уже отсортированы по рейтингу
            for _, row in top_movies.sample(min(20, len(top_movies))).iterrows():
                movie = row['Title']
                # IMDB dataset doesn't have director, use description for genre questions
                genre = row['Genres'].split(',')[0] if pd.notna(row['Genres']) else 'Unknown'
                
                wrong_genres = df[df['Genres'] != row['Genres']]['Genres'].dropna().str.split(',').str[0].drop_duplicates().sample(min(3, 10)).tolist()
                
                questions.append({
                    'text': f"What is the primary genre of the movie '{movie}'?",
                    'correct_answer': str(genre),
                    'wrong_answers': [str(g) for g in wrong_genres],
                    'category': 'ART',
                    'difficulty': 'MEDIUM'
                })
            
            # 2. Год выпуска
            for _, row in top_movies.sample(min(15, len(top_movies))).iterrows():
                movie = row['Title']
                year = row['Year']
                
                wrong_years = [str(year + random.randint(-20, 20)) for _ in range(3)]
                
                questions.append({
                    'text': f"When was the movie '{movie}' released?",
                    'correct_answer': str(year),
                    'wrong_answers': wrong_years,
                    'category': 'ART',
                    'difficulty': 'MEDIUM'
                })
            
            # 3. Рейтинг фильма
            for _, row in top_movies.head(10).iterrows():
                movie = row['Title']
                rating = row['Rating']
                
                wrong_ratings = [round(rating + random.uniform(-1, 1), 1) for _ in range(3)]
                
                questions.append({
                    'text': f"What is the IMDB rating of '{movie}'?",
                    'correct_answer': str(rating),
                    'wrong_answers': [str(r) for r in wrong_ratings],
                    'category': 'ART',
                    'difficulty': 'HARD'
                })
                
        except Exception as e:
            print(f"Error processing movies: {e}")
        
        return questions[:40]
    
    def process_music(self) -> List[Dict]:
        """Генерирует вопросы из датасета о музыке Spotify."""
        questions = []
        
        csv_path = self.base_path / "spotify_songs" / "spotify-2023.csv"
        if not csv_path.exists():
            print(f"File not found: {csv_path}")
            return questions
        
        try:
            df = pd.read_csv(csv_path, encoding='latin1')
            print(f"Music: {len(df)} songs")
            
            # 1. Артисты популярных песен
            # Convert streams to numeric
            df['streams_num'] = pd.to_numeric(df['streams'], errors='coerce')
            top_songs = df.nlargest(50, 'streams_num')
            for _, row in top_songs.sample(min(20, len(top_songs))).iterrows():
                song = row['track_name']
                artist = row['artist(s)_name'].split(',')[0] if pd.notna(row['artist(s)_name']) else 'Unknown'
                
                wrong_artists = df[df['artist(s)_name'] != row['artist(s)_name']]['artist(s)_name'].dropna().str.split(',').str[0].drop_duplicates().sample(min(3, 10)).tolist()
                
                questions.append({
                    'text': f"Who performed the song '{song}'?",
                    'correct_answer': str(artist),
                    'wrong_answers': [str(a) for a in wrong_artists],
                    'category': 'ART',
                    'difficulty': 'MEDIUM'
                })
            
            # 2. Год выпуска
            for _, row in top_songs.sample(min(15, len(top_songs))).iterrows():
                song = row['track_name']
                year = row['released_year']
                
                wrong_years = [str(int(year) + random.randint(-5, 5)) for _ in range(3)]
                
                questions.append({
                    'text': f"When was the song '{song}' released?",
                    'correct_answer': str(year),
                    'wrong_answers': wrong_years,
                    'category': 'ART',
                    'difficulty': 'HARD'
                })
                
        except Exception as e:
            print(f"Error processing music: {e}")
        
        return questions[:30]

    def process_olympics(self) -> List[Dict]:
        """Генерирует вопросы из датасета об Олимпийских играх."""
        questions = []
        
        csv_path = self.base_path / "olympics" / "athlete_events.csv"
        if not csv_path.exists():
            print(f"File not found: {csv_path}")
            return questions
        
        try:
            df = pd.read_csv(csv_path)
            print(f"Olympics: {len(df)} athlete records")
            
            # 1. Города Олимпиад
            games = df.groupby(['Year', 'Season', 'City']).size().reset_index()
            games = games.sample(min(20, len(games)))
            
            for _, row in games.iterrows():
                year = row['Year']
                season = row['Season']
                city = row['City']
                
                # Получаем другие города
                wrong_cities = df[df['City'] != city]['City'].drop_duplicates().sample(min(3, 10)).tolist()
                
                questions.append({
                    'text': f"Which city hosted the {year} {season} Olympics?",
                    'correct_answer': str(city),
                    'wrong_answers': [str(c) for c in wrong_cities],
                    'category': 'SPORT',
                    'difficulty': 'MEDIUM'
                })
            
            # 2. Страны с наибольшим количеством медалей
            medals = df[df['Medal'].notna()]
            top_countries = medals.groupby('Team')['Medal'].count().sort_values(ascending=False).head(15)
            
            for country in top_countries.index[:10]:
                count = top_countries[country]
                
                wrong_countries = top_countries.index[10:13].tolist()
                
                questions.append({
                    'text': f"Which country has won {count} Olympic medals (all time)?",
                    'correct_answer': str(country),
                    'wrong_answers': [str(c) for c in wrong_countries],
                    'category': 'SPORT',
                    'difficulty': 'HARD'
                })
            
            # 3. Спортсмены с наибольшим количеством медалей
            top_athletes = medals.groupby('Name')['Medal'].count().sort_values(ascending=False).head(10)
            
            for athlete in top_athletes.index[:5]:
                count = top_athletes[athlete]
                
                wrong_athletes = top_athletes.index[5:8].tolist()
                
                # Короткое имя
                short_name = athlete.split(',')[0] if ',' in athlete else athlete
                wrong_short = [a.split(',')[0] if ',' in a else a for a in wrong_athletes]
                
                questions.append({
                    'text': f"Who is the Olympian with {count} medals (one of the greatest)?",
                    'correct_answer': str(short_name),
                    'wrong_answers': wrong_short,
                    'category': 'SPORT',
                    'difficulty': 'HARD'
                })
            
            # 4. Виды спорта
            sports = df.groupby('Sport').size().sort_values(ascending=False).head(20)
            for sport in sports.index[:10]:
                wrong_sports = sports.index[10:13].tolist()
                
                questions.append({
                    'text': f"Which sport has been part of the Olympics for decades?",
                    'correct_answer': str(sport),
                    'wrong_answers': [str(s) for s in wrong_sports],
                    'category': 'SPORT',
                    'difficulty': 'EASY'
                })
                
        except Exception as e:
            print(f"Error processing olympics: {e}")
        
        return questions[:40]
    
    def save_questions(self, output_path: str = "data/kaggle_questions.json"):
        """Обрабатывает все датасеты и сохраняет вопросы."""
        all_questions = []
        
        # Обрабатываем каждый датасет
        processors = [
            ("World Population", self.process_world_population()),
            ("Russian Literature", self.process_russian_literature()),
            ("Olympics", self.process_olympics()),
        ]
        
        for name, questions in processors:
            print(f"\n{name}: {len(questions)} questions generated")
            all_questions.extend(questions)
            
        # Дополнительные датасеты
        extra_questions = self.process_movies()
        print(f"\nMovies: {len(extra_questions)} questions generated")
        all_questions.extend(extra_questions)
        
        music_questions = self.process_music()
        print(f"\nMusic: {len(music_questions)} questions generated")
        all_questions.extend(music_questions)
        
        # Сохраняем
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Total questions generated: {len(all_questions)}")
        print(f"Saved to: {output_path}")
        print(f"{'='*60}")
        
        return all_questions


if __name__ == "__main__":
    print("="*60)
    print("Kaggle Datasets Processor")
    print("="*60)
    
    processor = KaggleDataProcessor()
    processor.save_questions()
