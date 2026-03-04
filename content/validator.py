"""5-уровневая валидация вопросов.

Обеспечивает качество контента перед добавлением в базу.

Example:
    >>> from content.validator import ContentValidator
    >>> validator = ContentValidator()
    >>> result = await validator.validate_question(question_data)
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, func

from db import get_db
from models import Question


logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Уровни валидации."""
    STRUCTURE = 1
    LENGTH = 2
    SEMANTIC = 3
    UNIQUENESS = 4
    DIFFICULTY = 5


class ValidationSeverity(Enum):
    """Серьёзность проблемы."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Проблема валидации.
    
    Attributes:
        level: Уровень валидации
        severity: Серьёзность
        message: Сообщение
        field: Поле с проблемой
    """
    level: ValidationLevel
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None


@dataclass
class ValidationReport:
    """Отчёт о валидации.
    
    Attributes:
        is_valid: Прошла ли валидация
        issues: Список проблем
        score: Оценка качества (0-100)
    """
    is_valid: bool
    issues: List[ValidationIssue]
    score: float
    
    def get_errors(self) -> List[ValidationIssue]:
        """Получает только ошибки.
        
        Returns:
            List[ValidationIssue]: Список ошибок
        """
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Получает только предупреждения.
        
        Returns:
            List[ValidationIssue]: Список предупреждений
        """
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class ContentValidator:
    """Валидатор контента с 5 уровнями проверки."""
    
    # Константы
    MIN_QUESTION_LENGTH = 10
    MAX_QUESTION_LENGTH = 500
    MIN_ANSWER_LENGTH = 1
    MAX_ANSWER_LENGTH = 200
    MIN_WRONG_ANSWERS = 3
    MAX_WRONG_ANSWERS = 3
    
    # Запрещённые слова и паттерны
    FORBIDDEN_WORDS = [
        "xxx", "porn", "sex", "нахуй", "блядь", "пиздец",
        "сука", "ебать", "хуй", "пизда", "блять", "еблан",
        "мудак", "гандон", "шлюха", "проститутка"
    ]
    
    # Паттерны для проверки
    URL_PATTERN = re.compile(r'https?://\S+')
    EMAIL_PATTERN = re.compile(r'\S+@\S+\.\S+')
    PHONE_PATTERN = re.compile(r'\+?\d{10,}')
    
    # Минимальная оценка для прохождения
    MIN_SCORE = 70.0
    
    def __init__(self):
        """Инициализирует валидатор."""
        self._duplicate_cache: Set[str] = set()
    
    async def validate_question(
        self,
        question_data: Dict[str, Any],
        skip_levels: Optional[List[ValidationLevel]] = None
    ) -> ValidationReport:
        """Выполняет полную валидацию вопроса.
        
        Args:
            question_data: Данные вопроса
            skip_levels: Уровни для пропуска
            
        Returns:
            ValidationReport: Отчёт о валидации
        """
        skip_levels = skip_levels or []
        issues: List[ValidationIssue] = []
        
        # Уровень 1: Структурная валидация
        if ValidationLevel.STRUCTURE not in skip_levels:
            issues.extend(self._validate_structure(question_data))
        
        # Уровень 2: Валидация длины
        if ValidationLevel.LENGTH not in skip_levels:
            issues.extend(self._validate_length(question_data))
        
        # Уровень 3: Семантическая валидация
        if ValidationLevel.SEMANTIC not in skip_levels:
            issues.extend(self._validate_semantic(question_data))
        
        # Уровень 4: Валидация уникальности
        if ValidationLevel.UNIQUENESS not in skip_levels:
            uniqueness_issues = await self._validate_uniqueness(question_data)
            issues.extend(uniqueness_issues)
        
        # Уровень 5: Валидация сложности
        if ValidationLevel.DIFFICULTY not in skip_levels:
            issues.extend(self._validate_difficulty(question_data))
        
        # Вычисляем оценку
        score = self._calculate_score(issues)
        
        # Проверяем валидность
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        is_valid = len(errors) == 0 and score >= self.MIN_SCORE
        
        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            score=score
        )
    
    def _validate_structure(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Уровень 1: Проверка структуры.
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[ValidationIssue]: Список проблем
        """
        issues = []
        required_fields = {
            "text": str,
            "correct_answer": str,
            "wrong_answers": list,
            "category": str,
        }
        
        for field, field_type in required_fields.items():
            if field not in data:
                issues.append(ValidationIssue(
                    level=ValidationLevel.STRUCTURE,
                    severity=ValidationSeverity.ERROR,
                    message=f"Отсутствует обязательное поле: {field}",
                    field=field
                ))
            elif not isinstance(data[field], field_type):
                issues.append(ValidationIssue(
                    level=ValidationLevel.STRUCTURE,
                    severity=ValidationSeverity.ERROR,
                    message=f"Неверный тип поля {field}: ожидается {field_type.__name__}",
                    field=field
                ))
        
        # Проверка wrong_answers
        if "wrong_answers" in data:
            wrong_answers = data["wrong_answers"]
            
            if len(wrong_answers) < self.MIN_WRONG_ANSWERS:
                issues.append(ValidationIssue(
                    level=ValidationLevel.STRUCTURE,
                    severity=ValidationSeverity.ERROR,
                    message=f"Недостаточно неправильных ответов: {len(wrong_answers)} < {self.MIN_WRONG_ANSWERS}",
                    field="wrong_answers"
                ))
            
            if len(wrong_answers) > self.MAX_WRONG_ANSWERS:
                issues.append(ValidationIssue(
                    level=ValidationLevel.STRUCTURE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Слишком много неправильных ответов: {len(wrong_answers)} > {self.MAX_WRONG_ANSWERS}",
                    field="wrong_answers"
                ))
        
        return issues
    
    def _validate_length(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Уровень 2: Проверка длины.
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[ValidationIssue]: Список проблем
        """
        issues = []
        
        # Проверка вопроса
        question_text = data.get("text", "")
        q_length = len(question_text)
        
        if q_length < self.MIN_QUESTION_LENGTH:
            issues.append(ValidationIssue(
                level=ValidationLevel.LENGTH,
                severity=ValidationSeverity.ERROR,
                message=f"Вопрос слишком короткий: {q_length} < {self.MIN_QUESTION_LENGTH} символов",
                field="text"
            ))
        elif q_length > self.MAX_QUESTION_LENGTH:
            issues.append(ValidationIssue(
                level=ValidationLevel.LENGTH,
                severity=ValidationSeverity.ERROR,
                message=f"Вопрос слишком длинный: {q_length} > {self.MAX_QUESTION_LENGTH} символов",
                field="text"
            ))
        
        # Проверка правильного ответа
        correct = data.get("correct_answer", "")
        c_length = len(correct)
        
        if c_length < self.MIN_ANSWER_LENGTH:
            issues.append(ValidationIssue(
                level=ValidationLevel.LENGTH,
                severity=ValidationSeverity.ERROR,
                message="Правильный ответ пустой",
                field="correct_answer"
            ))
        elif c_length > self.MAX_ANSWER_LENGTH:
            issues.append(ValidationIssue(
                level=ValidationLevel.LENGTH,
                severity=ValidationSeverity.WARNING,
                message=f"Правильный ответ слишком длинный: {c_length} > {self.MAX_ANSWER_LENGTH} символов",
                field="correct_answer"
            ))
        
        # Проверка неправильных ответов
        for i, answer in enumerate(data.get("wrong_answers", [])):
            a_length = len(answer)
            
            if a_length < self.MIN_ANSWER_LENGTH:
                issues.append(ValidationIssue(
                    level=ValidationLevel.LENGTH,
                    severity=ValidationSeverity.ERROR,
                    message=f"Неправильный ответ {i+1} пустой",
                    field=f"wrong_answers[{i}]"
                ))
            elif a_length > self.MAX_ANSWER_LENGTH:
                issues.append(ValidationIssue(
                    level=ValidationLevel.LENGTH,
                    severity=ValidationSeverity.WARNING,
                    message=f"Неправильный ответ {i+1} слишком длинный",
                    field=f"wrong_answers[{i}]"
                ))
        
        return issues
    
    def _validate_semantic(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Уровень 3: Семантическая проверка.
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[ValidationIssue]: Список проблем
        """
        issues = []
        
        question_text = data.get("text", "").lower()
        correct_answer = data.get("correct_answer", "").lower()
        wrong_answers = [a.lower() for a in data.get("wrong_answers", [])]
        
        # Проверка на запрещённые слова
        for word in self.FORBIDDEN_WORDS:
            if word in question_text:
                issues.append(ValidationIssue(
                    level=ValidationLevel.SEMANTIC,
                    severity=ValidationSeverity.ERROR,
                    message=f"Вопрос содержит запрещённое слово: {word}",
                    field="text"
                ))
            
            if word in correct_answer:
                issues.append(ValidationIssue(
                    level=ValidationLevel.SEMANTIC,
                    severity=ValidationSeverity.ERROR,
                    message=f"Правильный ответ содержит запрещённое слово: {word}",
                    field="correct_answer"
                ))
        
        # Проверка на дубликаты ответов
        all_answers = [correct_answer] + wrong_answers
        if len(all_answers) != len(set(all_answers)):
            issues.append(ValidationIssue(
                level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.ERROR,
                message="Обнаружены дублирующиеся ответы",
                field="answers"
            ))
        
        # Проверка на содержание ответа в вопросе
        if correct_answer in question_text:
            issues.append(ValidationIssue(
                level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Правильный ответ содержится в тексте вопроса",
                field="text"
            ))
        
        # Проверка на вопросительный знак
        if not question_text.strip().endswith("?"):
            issues.append(ValidationIssue(
                level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Вопрос не заканчивается вопросительным знаком",
                field="text"
            ))
        
        # Проверка на URL
        if self.URL_PATTERN.search(question_text):
            issues.append(ValidationIssue(
                level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Вопрос содержит URL",
                field="text"
            ))
        
        # Проверка на email
        if self.EMAIL_PATTERN.search(question_text):
            issues.append(ValidationIssue(
                level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Вопрос содержит email",
                field="text"
            ))
        
        # Проверка схожести ответов (простая)
        for i, ans1 in enumerate(all_answers):
            for j, ans2 in enumerate(all_answers):
                if i < j:
                    similarity = self._calculate_similarity(ans1, ans2)
                    if similarity > 0.8:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.SEMANTIC,
                            severity=ValidationSeverity.WARNING,
                            message=f"Ответы {i+1} и {j+1} слишком похожи ({similarity:.0%})",
                            field="answers"
                        ))
        
        return issues
    
    async def _validate_uniqueness(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Уровень 4: Проверка уникальности.
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[ValidationIssue]: Список проблем
        """
        issues = []
        question_text = data.get("text", "").strip().lower()
        
        # Проверка в локальном кэше
        if question_text in self._duplicate_cache:
            issues.append(ValidationIssue(
                level=ValidationLevel.UNIQUENESS,
                severity=ValidationSeverity.ERROR,
                message="Вопрос уже обработан в текущей сессии",
                field="text"
            ))
            return issues
        
        # Проверка в базе данных
        async with get_db() as db:
            result = await db.execute(
                select(Question).where(
                    func.lower(func.trim(Question.text)) == question_text
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                issues.append(ValidationIssue(
                    level=ValidationLevel.UNIQUENESS,
                    severity=ValidationSeverity.ERROR,
                    message=f"Вопрос уже существует в базе (ID: {existing.id})",
                    field="text"
                ))
            else:
                # Добавляем в кэш
                self._duplicate_cache.add(question_text)
        
        return issues
    
    def _validate_difficulty(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Уровень 5: Проверка сложности.
        
        Args:
            data: Данные вопроса
            
        Returns:
            List[ValidationIssue]: Список проблем
        """
        issues = []
        
        difficulty = data.get("difficulty", "").lower()
        valid_difficulties = ["easy", "medium", "hard"]
        
        if difficulty not in valid_difficulties:
            issues.append(ValidationIssue(
                level=ValidationLevel.DIFFICULTY,
                severity=ValidationSeverity.WARNING,
                message=f"Необычный уровень сложности: {difficulty}",
                field="difficulty"
            ))
        
        # Проверка длины как индикатора сложности
        question_text = data.get("text", "")
        if difficulty == "easy" and len(question_text) > 200:
            issues.append(ValidationIssue(
                level=ValidationLevel.DIFFICULTY,
                severity=ValidationSeverity.INFO,
                message="Длинный вопрос помечен как 'лёгкий'",
                field="difficulty"
            ))
        
        return issues
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Вычисляет схожесть двух строк (простая реализация).
        
        Args:
            s1: Первая строка
            s2: Вторая строка
            
        Returns:
            float: Коэффициент схожести (0-1)
        """
        # Простая реализация на основе расстояния Левенштейна
        if len(s1) < len(s2):
            return self._calculate_similarity(s2, s1)
        
        if len(s2) == 0:
            return 0.0
        
        # Нормализуем
        s1 = s1.lower().strip()
        s2 = s2.lower().strip()
        
        # Если строки одинаковые
        if s1 == s2:
            return 1.0
        
        # Если одна строка содержит другую
        if s1 in s2 or s2 in s1:
            return 0.9
        
        # Подсчёт общих слов
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """Вычисляет итоговую оценку качества.
        
        Args:
            issues: Список проблем
            
        Returns:
            float: Оценка (0-100)
        """
        score = 100.0
        
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                score -= 20
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 10
            elif issue.severity == ValidationSeverity.INFO:
                score -= 2
        
        return max(0.0, score)
    
    def clear_cache(self) -> None:
        """Очищает кэш дубликатов."""
        self._duplicate_cache.clear()
        logger.info("Duplicate cache cleared")


class BatchValidator:
    """Валидатор для пакетной обработки вопросов."""
    
    def __init__(self, validator: Optional[ContentValidator] = None):
        """Инициализирует пакетный валидатор.
        
        Args:
            validator: Экземпляр валидатора
        """
        self.validator = validator or ContentValidator()
    
    async def validate_batch(
        self,
        questions: List[Dict[str, Any]],
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """Валидирует пакет вопросов.
        
        Args:
            questions: Список вопросов
            stop_on_error: Останавливаться при первой ошибке
            
        Returns:
            Dict: Статистика валидации
        """
        results = {
            "total": len(questions),
            "valid": 0,
            "invalid": 0,
            "errors": 0,
            "warnings": 0,
            "details": []
        }
        
        for i, question in enumerate(questions):
            report = await self.validator.validate_question(question)
            
            detail = {
                "index": i,
                "is_valid": report.is_valid,
                "score": report.score,
                "errors": len(report.get_errors()),
                "warnings": len(report.get_warnings())
            }
            results["details"].append(detail)
            
            if report.is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            
            results["errors"] += len(report.get_errors())
            results["warnings"] += len(report.get_warnings())
            
            if stop_on_error and not report.is_valid:
                break
        
        return results


# Глобальные экземпляры
content_validator = ContentValidator()
batch_validator = BatchValidator()
