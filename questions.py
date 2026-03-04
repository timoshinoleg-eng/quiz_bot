"""Загрузка, выборка и валидация вопросов.

Этот модуль отвечает за:
- Загрузку вопросов из внешних источников (RuBQ, OpenTriviaDB)
- Валидацию вопросов
- Выборку случайных вопросов для игр
- Кэширование вопросов

Example:
    >>> from questions import QuestionLoader
    >>> loader = QuestionLoader()
    >>> await loader.load_from_rubq("rubq_data.json")
"""

import json
import logging
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import aiohttp
from sqlalchemy import select, func

from db import get_db, db_manager
from models import Question, QuestionCategory, DifficultyLevel


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Результат валидации вопроса.
    
    Attributes:
        is_valid: Прошёл ли вопрос валидацию
        errors: Список ошибок
        warnings: Список предупреждений
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class QuestionValidator:
    """Валидатор вопросов с 5-уровневой проверкой.
    
    Уровни валидации:
    1. Структурная валидация (обязательные поля)
    2. Валидация длины (вопрос и ответы)
    3. Семантическая валидация (смысл вопроса)
    4. Валидация уникальности (дубликаты)
    5. Валидация сложности (распределение)
    """
    
    # Константы для валидации
    MIN_QUESTION_LENGTH = 10
    MAX_QUESTION_LENGTH = 500
    MIN_ANSWER_LENGTH = 1
    MAX_ANSWER_LENGTH = 200
    MIN_WRONG_ANSWERS = 3
    
    # Запрещённые слова
    FORBIDDEN_WORDS = [
        "xxx", "porn", "sex", "нахуй", "блядь", "пиздец",
        "сука", "ебать", "хуй", "пизда"
    ]
    
    async def validate(
        self,
        question_data: Dict[str, Any],
        check_duplicate: bool = True
    ) -> ValidationResult:
        """Выполняет полную валидацию вопроса.
        
        Args:
            question_data: Данные вопроса
            check_duplicate: Проверять ли дубликаты
            
        Returns:
            ValidationResult: Результат валидации
        """
        errors = []
        warnings = []
        
        # Уровень 1: Структурная валидация
        struct_result = self._validate_structure(question_data)
        errors.extend(struct_result)
        
        # Уровень 2: Валидация длины
        length_result = self._validate_length(question_data)
        errors.extend(length_result)
        
        # Уровень 3: Семантическая валидация
        semantic_result = self._validate_semantic(question_data)
        errors.extend(semantic_result["errors"])
        warnings.extend(semantic_result["warnings"])
        
        # Уровень 4: Валидация уникальности
        if check_duplicate:
            dup_result = await self._validate_uniqueness(question_data)
            if dup_result:
                errors.append(dup_result)
        
        # Уровень 5: Валидация сложности
        difficulty_result = self._validate_difficulty(question_data)
        warnings.extend(difficulty_result)
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Question validation failed: {errors}")
        
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
    
    def _validate_structure(self, data: Dict[str, Any]) -> List[str]:
        """Проверяет структуру вопроса (Уровень 1).
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[str]: Список ошибок
        """
        errors = []
        required_fields = ["text", "correct_answer", "wrong_answers", "category"]
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        if "wrong_answers" in data:
            wrong_answers = data["wrong_answers"]
            if not isinstance(wrong_answers, list):
                errors.append("wrong_answers must be a list")
            elif len(wrong_answers) < self.MIN_WRONG_ANSWERS:
                errors.append(f"At least {self.MIN_WRONG_ANSWERS} wrong answers required")
        
        return errors
    
    def _validate_length(self, data: Dict[str, Any]) -> List[str]:
        """Проверяет длину полей (Уровень 2).
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[str]: Список ошибок
        """
        errors = []
        
        question_text = data.get("text", "")
        if len(question_text) < self.MIN_QUESTION_LENGTH:
            errors.append(f"Question too short (< {self.MIN_QUESTION_LENGTH} chars)")
        if len(question_text) > self.MAX_QUESTION_LENGTH:
            errors.append(f"Question too long (> {self.MAX_QUESTION_LENGTH} chars)")
        
        correct_answer = data.get("correct_answer", "")
        if len(correct_answer) < self.MIN_ANSWER_LENGTH:
            errors.append("Correct answer is empty")
        if len(correct_answer) > self.MAX_ANSWER_LENGTH:
            errors.append(f"Correct answer too long (> {self.MAX_ANSWER_LENGTH} chars)")
        
        for i, answer in enumerate(data.get("wrong_answers", [])):
            if len(answer) < self.MIN_ANSWER_LENGTH:
                errors.append(f"Wrong answer {i+1} is empty")
            if len(answer) > self.MAX_ANSWER_LENGTH:
                errors.append(f"Wrong answer {i+1} too long")
        
        return errors
    
    def _validate_semantic(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Проверяет семантику вопроса (Уровень 3).
        
        Args:
            data: Данные вопроса
            
        Returns:
            Dict с errors и warnings
        """
        errors = []
        warnings = []
        
        question_text = data.get("text", "").lower()
        correct_answer = data.get("correct_answer", "").lower()
        wrong_answers = [a.lower() for a in data.get("wrong_answers", [])]
        
        # Проверка на запрещённые слова
        for word in self.FORBIDDEN_WORDS:
            if word in question_text or word in correct_answer:
                errors.append(f"Contains forbidden word: {word}")
        
        # Проверка на дубликаты ответов
        all_answers = [correct_answer] + wrong_answers
        if len(all_answers) != len(set(all_answers)):
            errors.append("Duplicate answers detected")
        
        # Проверка на содержание ответа в вопросе
        if correct_answer in question_text:
            warnings.append("Correct answer appears in question text")
        
        # Проверка на вопросительный знак
        if not question_text.strip().endswith("?"):
            warnings.append("Question doesn't end with question mark")
        
        return {"errors": errors, "warnings": warnings}
    
    async def _validate_uniqueness(self, data: Dict[str, Any]) -> Optional[str]:
        """Проверяет уникальность вопроса (Уровень 4).
        
        Args:
            data: Данные вопроса
            
        Returns:
            Optional[str]: Ошибка если не уникален
        """
        question_text = data.get("text", "")
        
        async with get_db() as db:
            result = await db.execute(
                select(Question).where(
                    func.lower(Question.text) == question_text.lower()
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return f"Duplicate question found (ID: {existing.id})"
        
        return None
    
    def _validate_difficulty(self, data: Dict[str, Any]) -> List[str]:
        """Проверяет корректность сложности (Уровень 5).
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[str]: Список предупреждений
        """
        warnings = []
        difficulty = data.get("difficulty", "")
        
        valid_difficulties = [d.value for d in DifficultyLevel]
        if difficulty not in valid_difficulties:
            warnings.append(f"Unusual difficulty level: {difficulty}")
        
        return warnings


class QuestionLoader:
    """Загрузчик вопросов из внешних источников."""
    
    def __init__(self):
        self.validator = QuestionValidator()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создаёт HTTP сессию.
        
        Returns:
            aiohttp.ClientSession: HTTP сессия
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self) -> None:
        """Закрывает HTTP сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def load_from_rubq(
        self,
        file_path: str,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """Загружает вопросы из RuBQ JSON файла.
        
        Args:
            file_path: Путь к JSON файлу
            limit: Ограничение количества вопросов
            
        Returns:
            Dict с статистикой загрузки
        """
        logger.info(f"Loading questions from RuBQ: {file_path}")
        
        stats = {"total": 0, "loaded": 0, "errors": 0, "skipped": 0}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            questions = data if isinstance(data, list) else data.get("questions", [])
            
            if limit:
                questions = questions[:limit]
            
            stats["total"] = len(questions)
            
            for q_data in questions:
                try:
                    # Преобразуем формат RuBQ в наш формат
                    question_dict = self._convert_rubq_format(q_data)
                    
                    # Валидация
                    validation = await self.validator.validate(question_dict)
                    
                    if not validation.is_valid:
                        logger.warning(
                            f"Validation failed for question: {validation.errors}"
                        )
                        stats["errors"] += 1
                        continue
                    
                    # Сохранение в БД
                    await self._save_question(question_dict)
                    stats["loaded"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing question: {e}")
                    stats["errors"] += 1
            
            logger.info(f"RuBQ loading complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to load RuBQ file: {e}")
            raise
    
    def _convert_rubq_format(self, rubq_data: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует формат RuBQ в наш формат.
        
        Args:
            rubq_data: Данные вопроса из RuBQ
            
        Returns:
            Dict: Данные в нашем формате
        """
        # Маппинг категорий RuBQ на наши
        category_mapping = {
            "History": QuestionCategory.HISTORY,
            "Science": QuestionCategory.SCIENCE,
            "Art": QuestionCategory.ART,
            "Sports": QuestionCategory.SPORTS,
            "Geography": QuestionCategory.GEOGRAPHY,
            "Entertainment": QuestionCategory.ENTERTAINMENT,
        }
        
        category = category_mapping.get(
            rubq_data.get("category", ""),
            QuestionCategory.GENERAL
        )
        
        # Определяем сложность
        difficulty_str = rubq_data.get("difficulty", "medium").lower()
        difficulty_map = {
            "easy": DifficultyLevel.EASY,
            "medium": DifficultyLevel.MEDIUM,
            "hard": DifficultyLevel.HARD,
        }
        difficulty = difficulty_map.get(difficulty_str, DifficultyLevel.MEDIUM)
        
        return {
            "text": rubq_data.get("question", ""),
            "correct_answer": rubq_data.get("correct_answer", ""),
            "wrong_answers": rubq_data.get("incorrect_answers", []),
            "explanation": rubq_data.get("explanation", ""),
            "category": category,
            "difficulty": difficulty,
            "source": "rubq",
            "source_id": str(rubq_data.get("id", "")),
        }
    
    async def load_from_opentdb(
        self,
        amount: int = 50,
        category: Optional[int] = None,
        difficulty: Optional[str] = None
    ) -> Dict[str, int]:
        """Загружает вопросы из Open Trivia Database API.
        
        Args:
            amount: Количество вопросов
            category: ID категории (опционально)
            difficulty: Сложность (easy, medium, hard)
            
        Returns:
            Dict с статистикой загрузки
        """
        logger.info(f"Loading questions from OpenTDB: amount={amount}")
        
        url = "https://opentdb.com/api.php"
        params = {"amount": amount, "type": "multiple"}
        
        if category:
            params["category"] = category
        if difficulty:
            params["difficulty"] = difficulty
        
        stats = {"total": 0, "loaded": 0, "errors": 0}
        
        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                data = await response.json()
            
            if data.get("response_code") != 0:
                logger.error(f"OpenTDB API error: {data.get('response_code')}")
                return stats
            
            questions = data.get("results", [])
            stats["total"] = len(questions)
            
            for q_data in questions:
                try:
                    question_dict = self._convert_opentdb_format(q_data)
                    
                    validation = await self.validator.validate(question_dict)
                    
                    if not validation.is_valid:
                        stats["errors"] += 1
                        continue
                    
                    await self._save_question(question_dict)
                    stats["loaded"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing OpenTDB question: {e}")
                    stats["errors"] += 1
            
            logger.info(f"OpenTDB loading complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to load from OpenTDB: {e}")
            raise
    
    def _convert_opentdb_format(self, opentdb_data: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует формат OpenTDB в наш формат.
        
        Args:
            opentdb_data: Данные вопроса из OpenTDB
            
        Returns:
            Dict: Данные в нашем формате
        """
        import html
        
        # Декодируем HTML entities
        question_text = html.unescape(opentdb_data.get("question", ""))
        correct_answer = html.unescape(opentdb_data.get("correct_answer", ""))
        wrong_answers = [html.unescape(a) for a in opentdb_data.get("incorrect_answers", [])]
        
        # Маппинг категорий
        category_str = opentdb_data.get("category", "")
        category_mapping = {
            "History": QuestionCategory.HISTORY,
            "Science": QuestionCategory.SCIENCE,
            "Art": QuestionCategory.ART,
            "Sports": QuestionCategory.SPORTS,
            "Geography": QuestionCategory.GEOGRAPHY,
            "Entertainment": QuestionCategory.ENTERTAINMENT,
        }
        
        # Пытаемся найти подходящую категорию
        category = QuestionCategory.GENERAL
        for key, value in category_mapping.items():
            if key.lower() in category_str.lower():
                category = value
                break
        
        difficulty_str = opentdb_data.get("difficulty", "medium")
        difficulty_map = {
            "easy": DifficultyLevel.EASY,
            "medium": DifficultyLevel.MEDIUM,
            "hard": DifficultyLevel.HARD,
        }
        difficulty = difficulty_map.get(difficulty_str, DifficultyLevel.MEDIUM)
        
        return {
            "text": question_text,
            "correct_answer": correct_answer,
            "wrong_answers": wrong_answers,
            "explanation": "",
            "category": category,
            "difficulty": difficulty,
            "source": "opentdb",
            "source_id": None,
        }
    
    async def _save_question(self, question_dict: Dict[str, Any]) -> None:
        """Сохраняет вопрос в базу данных.
        
        Args:
            question_dict: Данные вопроса
        """
        async with get_db() as db:
            question = Question(
                text=question_dict["text"],
                correct_answer=question_dict["correct_answer"],
                wrong_answers=question_dict["wrong_answers"],
                explanation=question_dict.get("explanation"),
                category=question_dict["category"],
                difficulty=question_dict["difficulty"],
                source=question_dict["source"],
                source_id=question_dict.get("source_id"),
            )
            db.add(question)


class QuestionManager:
    """Менеджер для работы с вопросами в игре."""
    
    @staticmethod
    async def get_questions_for_game(
        category: QuestionCategory,
        difficulty: DifficultyLevel,
        count: int = 10
    ) -> List[Question]:
        """Получает случайные вопросы для игры.
        
        Args:
            category: Категория
            difficulty: Сложность
            count: Количество вопросов
            
        Returns:
            List[Question]: Список вопросов
        """
        return await db_manager.get_random_questions(category, difficulty, count)
    
    @staticmethod
    def shuffle_answers(question: Question) -> List[tuple]:
        """Перемешивает ответы для отображения.
        
        Args:
            question: Вопрос
            
        Returns:
            List[tuple]: Список (текст ответа, is_correct)
        """
        answers = [(question.correct_answer, True)]
        for wrong in question.wrong_answers:
            answers.append((wrong, False))
        
        random.shuffle(answers)
        return answers
    
    @staticmethod
    async def update_question_stats(
        question_id: int,
        was_correct: bool
    ) -> None:
        """Обновляет статистику использования вопроса.
        
        Args:
            question_id: ID вопроса
            was_correct: Был ли ответ правильным
        """
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Question).where(Question.id == question_id)
            )
            question = result.scalar_one_or_none()
            
            if question:
                question.usage_count += 1
                
                # Обновляем процент правильных ответов
                total_correct = question.correct_rate * (question.usage_count - 1)
                if was_correct:
                    total_correct += 1
                question.correct_rate = total_correct / question.usage_count


# Глобальные экземпляры
question_loader = QuestionLoader()
question_manager = QuestionManager()
