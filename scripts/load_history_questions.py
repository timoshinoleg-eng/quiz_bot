"""Загрузка вопросов по истории из датасета RuBQ 2.0 в базу данных MAX-Квиз."""
import asyncio
import json
import sys
import re
import random
from pathlib import Path
from typing import List, Dict, Optional

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка логирования
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoryQuestionLoader:
    """Загрузчик вопросов по истории из RuBQ 2.0."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.stats = {
            "loaded": 0,
            "skipped": 0,
            "errors": 0,
            "history_filtered": 0
        }
        
        # Пул исторических ответов для генерации distractors
        self.history_pool = [
            'Петр I', 'Петр II', 'Петр III', 'Екатерина I', 'Екатерина II',
            'Александр I', 'Александр II', 'Александр III', 'Николай I', 'Николай II',
            'Иван Грозный', 'Иван III', 'Иван IV', 'Владимир Ленин', 'Иосиф Сталин',
            'Лев Троцкий', 'Михаил Горбачев', 'Борис Ельцин', 'Владимир Путин',
            'Наполеон Бонапарт', 'Адольф Гитлер', 'Уинстон Черчилль', 'Франклин Рузвельт',
            '1914', '1917', '1939', '1941', '1945', '1991', '1812', '1905',
            'Москва', 'Санкт-Петербург', 'Киев', 'Новгород', 'Владимир',
            'Российская Империя', 'Советский Союз', 'РСФСР', 'Россия',
            'Первая мировая война', 'Вторая мировая война', 'Отечественная война 1812 года',
            'Октябрьская революция', 'Февральская революция', 'Гражданская война',
            'Бородинское сражение', 'Сталинградская битва', 'Курская дуга',
            'Битва при Сталинграде', 'Битва при Ватерлоо', 'Битва при Бородино',
            'Французская революция', 'Великая Отечественная война'
        ]
    
    async def load_parquet_file(self, file_path: str) -> List[Dict]:
        """Загрузка вопросов из Parquet файла."""
        try:
            import pandas as pd
            logger.info(f"Загрузка файла: {file_path}")
            df = pd.read_parquet(file_path)
            logger.info(f"Найдено {len(df)} вопросов в файле")
            return df.to_dict('records')
        except ImportError:
            logger.error("Требуется pandas: pip install pandas pyarrow")
            return []
        except Exception as e:
            logger.error(f"Ошибка чтения Parquet: {e}")
            return []
    
    def is_history_question(self, question_text: str, tags=None) -> bool:
        """Определение относится ли вопрос к истории."""
        history_keywords = [
            'история', 'война', 'царь', 'император', 'революция', 'год', 'век',
            'древний', 'средневеков', 'битва', 'армия', 'полководец', 'династия',
            'империя', 'королевство', 'республика', 'союз', 'договор', 'мир',
            'ссср', 'россия', 'советский', 'российский', 'петр', 'екатерина',
            'ленин', 'сталин', 'наполеон', 'гитлер', 'первая мировая', 
            'вторая мировая', 'отечественная война', 'октябрьская революция',
            'февральская', 'белое движение', 'красное движение', 'гражданская война',
            'политик', 'правитель', 'князь', 'король', 'президент', 'генерал',
            'маршал', 'адмирал', 'княжество', 'царство', 'штат', 'провинция',
            'племя', 'народ', 'цивилизация', 'культура', 'эпоха', 'период',
            'античность', 'средневековье', 'новое время', 'новейшее время'
        ]
        
        text_lower = question_text.lower()
        if any(kw in text_lower for kw in history_keywords):
            return True
        
        # Проверяем теги
        if tags is not None:
            try:
                # Handle numpy arrays and lists
                if hasattr(tags, 'tolist'):
                    tags = tags.tolist()
                if isinstance(tags, (list, tuple)):
                    tags_str = ' '.join(str(t).lower() for t in tags if t)
                    if any(kw in tags_str for kw in history_keywords):
                        return True
            except:
                pass
        
        return False
    
    def determine_difficulty(self, question_text: str, answer_text: str) -> str:
        """Определение сложности вопроса."""
        text_lower = question_text.lower()
        answer_lower = answer_text.lower()
        
        # EASY: известные факты, короткие ответы, простые вопросы
        easy_indicators = [
            'кто был первым', 'когда был', 'кто такой', 'что такое',
            'где находится', 'в каком году', 'какой город', 'какая страна',
            'кто правил', 'кто возглавлял'
        ]
        if any(ind in text_lower for ind in easy_indicators):
            return 'EASY'
        
        # HARD: специфичные даты, длинные ответы, редкие факты
        hard_indicators = [
            'сложный', 'трудный', 'редкий', 'уникальный', 'специфический',
            'детальный', 'малоизвестный', 'секретный', 'закрытый',
            'точная дата', 'конкретный день', 'подробности'
        ]
        if any(ind in text_lower for ind in hard_indicators):
            return 'HARD'
        
        # Сложность по длине ответа
        if len(answer_lower) > 100 or len(answer_lower.split()) > 10:
            return 'HARD'
        
        if len(answer_lower) < 30 or len(answer_lower.split()) < 4:
            return 'EASY'
        
        # MEDIUM: по умолчанию
        return 'MEDIUM'
    
    def extract_short_answer(self, answer_text: str) -> str:
        """Извлечение краткого ответа из полного текста."""
        # Если ответ короткий - оставляем как есть
        if len(answer_text) < 100:
            return answer_text.strip()
        
        # Пробуем найти имя/название в кавычках
        import re
        quoted = re.findall(r'["""]([^"""]+)["""]', answer_text)
        if quoted:
            return quoted[0].strip()[:100]
        
        # Пробуем взять первое предложение
        sentences = answer_text.split('.')
        if sentences:
            first = sentences[0].strip()
            if len(first) > 10:
                return first[:100]
        
        # Fallback: обрезаем до 100 символов
        return answer_text[:100].strip()
    
    def generate_wrong_answers(self, correct_answer: str) -> List[str]:
        """Генерация релевантных неправильных ответов для истории."""
        wrong = []
        correct_lower = correct_answer.lower()
        
        # Стратегия 1: Если ответ содержит год
        years = re.findall(r'\b(\d{4})\b', correct_answer)
        if years:
            year = int(years[0])
            # Генерируем соседние годы
            offsets = [-1, 1, -5] if random.random() > 0.5 else [1, -1, 5]
            wrong = [str(year + off) for off in offsets]
            return wrong[:3]
        
        # Стратегия 2: Если ответ есть в пуле исторических фигур
        pool_lower = {p.lower(): p for p in self.history_pool}
        if correct_lower in pool_lower:
            # Возвращаем другие значения из пула той же "категории"
            candidates = [p for p in self.history_pool if p.lower() != correct_lower]
            # Фильтруем по похожей длине
            candidates = [c for c in candidates if abs(len(c) - len(correct_answer)) < 10]
            if len(candidates) >= 3:
                return random.sample(candidates, 3)
        
        # Стратегия 3: Поиск похожих по длине ответов
        candidates = [p for p in self.history_pool if p.lower() != correct_lower]
        candidates.sort(key=lambda x: abs(len(x) - len(correct_answer)))
        if len(candidates) >= 3:
            return candidates[:3]
        
        # Fallback: общие варианты
        return [
            "Другой исторический период",
            "Альтернативная версия события", 
            "Неверная дата/имя"
        ]
    
    async def load_questions(self, dataset_paths: List[str]):
        """Загрузка вопросов из всех указанных файлов."""
        all_questions = []
        
        for path in dataset_paths:
            full_path = Path(path)
            if not full_path.exists():
                # Пробуем найти в RuBQ_2.0
                alt_path = Path('RuBQ_2.0') / 'data' / path
                if alt_path.exists():
                    full_path = alt_path
                else:
                    logger.warning(f"Файл не найден: {path}")
                    continue
            
            questions = await self.load_parquet_file(str(full_path))
            all_questions.extend(questions)
        
        logger.info(f"Всего загружено {len(all_questions)} вопросов из всех файлов")
        
        # Фильтрация по истории
        history_questions = [
            q for q in all_questions 
            if self.is_history_question(
                q.get('question_text', q.get('question', '')),
                q.get('tags', None)
            )
        ]
        
        self.stats["history_filtered"] = len(history_questions)
        logger.info(f"Отфильтровано {len(history_questions)} вопросов по истории")
        
        # Сохранение в JSON для проверки
        self._save_for_inspection(history_questions)
        
        # Загрузка в БД
        if self.db_manager:
            await self.save_to_database(history_questions)
        else:
            logger.info("DB manager not provided, skipping database save")
            # Сохраняем в JSON
            self._save_to_json(history_questions)
    
    def _save_for_inspection(self, questions: List[Dict]):
        """Сохранение выборки вопросов для проверки."""
        output_dir = Path('data/generated')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем первые 10 вопросов для проверки
        sample = questions[:10]
        sample_data = []
        for q in sample:
            question_text = q.get('question_text', q.get('question', ''))
            answer_text = q.get('answer_text', q.get('answer', ''))
            short_answer = self.extract_short_answer(answer_text)
            
            sample_data.append({
                'question': question_text,
                'full_answer': answer_text[:200],
                'short_answer': short_answer,
                'difficulty': self.determine_difficulty(question_text, answer_text),
                'wrong_answers': self.generate_wrong_answers(short_answer)
            })
        
        with open(output_dir / 'history_sample.json', 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено {len(sample_data)} примеров в data/generated/history_sample.json")
    
    def _save_to_json(self, questions: List[Dict]):
        """Сохранение всех вопросов в JSON."""
        output_dir = Path('data/generated')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        prepared = []
        for idx, q in enumerate(questions):
            try:
                question_text = q.get('question_text', q.get('question', '')).strip()
                answer_text = q.get('answer_text', q.get('answer', '')).strip()
                
                if not question_text or not answer_text:
                    continue
                
                short_answer = self.extract_short_answer(answer_text)
                difficulty = self.determine_difficulty(question_text, answer_text)
                wrong_answers = self.generate_wrong_answers(short_answer)
                
                prepared.append({
                    'text': question_text,
                    'correct_answer': short_answer,
                    'wrong_answers': wrong_answers,
                    'category': 'HISTORY',
                    'difficulty': difficulty,
                    'source': 'RuBQ 2.0',
                    'source_id': q.get('uid', f'rubq_{idx}')
                })
                
            except Exception as e:
                logger.error(f"Ошибка обработки вопроса {idx}: {e}")
                continue
        
        output_file = output_dir / 'history_questions.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(prepared, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено {len(prepared)} вопросов в {output_file}")
        self.stats["loaded"] = len(prepared)
    
    async def save_to_database(self, questions: List[Dict]):
        """Сохранение вопросов в базу данных."""
        if not self.db_manager:
            logger.error("DB manager not provided")
            return
        
        from db import db_manager
        
        for idx, q in enumerate(questions):
            try:
                question_text = q.get('question_text', q.get('question', '')).strip()
                answer_text = q.get('answer_text', q.get('answer', '')).strip()
                
                if not question_text or not answer_text:
                    self.stats["skipped"] += 1
                    continue
                
                # Проверка на дубликаты
                existing = await db_manager.get_question_by_text(question_text)
                if existing:
                    self.stats["skipped"] += 1
                    continue
                
                short_answer = self.extract_short_answer(answer_text)
                difficulty = self.determine_difficulty(question_text, answer_text)
                wrong_answers = self.generate_wrong_answers(short_answer)
                
                # Создание вопроса
                await db_manager.add_question(
                    text=question_text,
                    correct_answer=short_answer,
                    wrong_answers=wrong_answers,
                    category='HISTORY',
                    difficulty=difficulty
                )
                
                self.stats["loaded"] += 1
                
                if self.stats["loaded"] % 100 == 0:
                    logger.info(f"Загружено {self.stats['loaded']} вопросов...")
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке вопроса {idx}: {e}")
                self.stats["errors"] += 1
                continue
        
        logger.info(f"Итого загружено в БД: {self.stats['loaded']}")


async def main():
    """Основной скрипт загрузки."""
    logger.info("=" * 60)
    logger.info("Загрузка вопросов по истории из RuBQ 2.0")
    logger.info("=" * 60)
    
    # Пути к файлам RuBQ 2.0
    dataset_paths = [
        "RuBQ_2.0/data/test-00000-of-00001-d519841742f463e6.parquet",
        "RuBQ_2.0/data/dev-00000-of-00001-d7e3040a344e1e68.parquet",
    ]
    
    # Создаем загрузчик
    loader = HistoryQuestionLoader(db_manager=None)  # Пока без БД, сохраняем в JSON
    
    # Загрузка
    await loader.load_questions(dataset_paths)
    
    # Итоговая статистика
    logger.info("=" * 60)
    logger.info("Загрузка завершена!")
    logger.info(f"   Отфильтровано по истории: {loader.stats['history_filtered']}")
    logger.info(f"   Подготовлено вопросов: {loader.stats['loaded']}")
    logger.info(f"   Пропущено: {loader.stats['skipped']}")
    logger.info(f"   Ошибок: {loader.stats['errors']}")
    logger.info("=" * 60)
    
    # Показываем примеры
    logger.info("\nПримеры сохранены в: data/generated/history_sample.json")
    logger.info("Все вопросы сохранены в: data/generated/history_questions.json")


if __name__ == "__main__":
    asyncio.run(main())
