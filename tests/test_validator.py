"""Тесты валидатора контента.

Тестируют 5-уровневую валидацию вопросов.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from content.validator import (
    ContentValidator,
    BatchValidator,
    ValidationLevel,
    ValidationSeverity,
)


@pytest.fixture
def valid_question():
    """Фикстура для валидного вопроса."""
    return {
        "text": "Какой город является столицей Франции?",
        "correct_answer": "Париж",
        "wrong_answers": ["Лондон", "Берлин", "Мадрид"],
        "category": "geography",
        "difficulty": "easy"
    }


@pytest.fixture
def invalid_question():
    """Фикстура для невалидного вопроса."""
    return {
        "text": "Короткий?",
        "correct_answer": "",
        "wrong_answers": ["Ответ 1"],
        "category": "general",
        "difficulty": "invalid"
    }


class TestStructureValidation:
    """Тесты структурной валидации (Уровень 1)."""
    
    def test_valid_structure(self, valid_question):
        """Тест валидной структуры."""
        validator = ContentValidator()
        issues = validator._validate_structure(valid_question)
        
        assert len(issues) == 0
    
    def test_missing_required_field(self):
        """Тест отсутствия обязательного поля."""
        validator = ContentValidator()
        question = {
            "text": "Вопрос?",
            "correct_answer": "Ответ"
            # Нет wrong_answers и category
        }
        
        issues = validator._validate_structure(question)
        
        assert len(issues) > 0
        assert any("wrong_answers" in i.message for i in issues)
    
    def test_insufficient_wrong_answers(self):
        """Тест недостаточного количества неправильных ответов."""
        validator = ContentValidator()
        question = {
            "text": "Вопрос?",
            "correct_answer": "Ответ",
            "wrong_answers": ["Неправильный 1"],
            "category": "general"
        }
        
        issues = validator._validate_structure(question)
        
        assert any("Недостаточно" in i.message for i in issues)


class TestLengthValidation:
    """Тесты валидации длины (Уровень 2)."""
    
    def test_question_too_short(self):
        """Тест слишком короткого вопроса."""
        validator = ContentValidator()
        question = {
            "text": "Коротко?",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        issues = validator._validate_length(question)
        
        assert any("слишком короткий" in i.message for i in issues)
    
    def test_question_too_long(self):
        """Тест слишком длинного вопроса."""
        validator = ContentValidator()
        question = {
            "text": "А" * 501 + "?",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        issues = validator._validate_length(question)
        
        assert any("слишком длинный" in i.message for i in issues)
    
    def test_empty_answer(self):
        """Тест пустого ответа."""
        validator = ContentValidator()
        question = {
            "text": "Нормальный вопрос?",
            "correct_answer": "",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        issues = validator._validate_length(question)
        
        assert any("пустой" in i.message for i in issues)


class TestSemanticValidation:
    """Тесты семантической валидации (Уровень 3)."""
    
    def test_forbidden_word_in_question(self):
        """Тест запрещённого слова в вопросе."""
        validator = ContentValidator()
        question = {
            "text": "Какое слово плохое: сука?",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        issues = validator._validate_semantic(question)
        
        assert any("запрещённое слово" in i.message for i in issues)
    
    def test_duplicate_answers(self):
        """Тест дублирующихся ответов."""
        validator = ContentValidator()
        question = {
            "text": "Вопрос?",
            "correct_answer": "Ответ",
            "wrong_answers": ["Ответ", "Б", "В"]  # Дубликат
        }
        
        issues = validator._validate_semantic(question)
        
        assert any("дублирующиеся" in i.message for i in issues)
    
    def test_answer_in_question(self):
        """Тест ответа в тексте вопроса."""
        validator = ContentValidator()
        question = {
            "text": "Какой город является Парижем?",
            "correct_answer": "Париж",
            "wrong_answers": ["Лондон", "Берлин", "Мадрид"]
        }
        
        issues = validator._validate_semantic(question)
        
        assert any("содержится в тексте" in i.message for i in issues)
    
    def test_no_question_mark(self):
        """Тест отсутствия вопросительного знака."""
        validator = ContentValidator()
        question = {
            "text": "Это не вопрос",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        issues = validator._validate_semantic(question)
        
        assert any("вопросительным знаком" in i.message for i in issues)


class TestUniquenessValidation:
    """Тесты валидации уникальности (Уровень 4)."""
    
    @pytest.mark.asyncio
    async def test_duplicate_question(self):
        """Тест дублирующегося вопроса."""
        validator = ContentValidator()
        question = {
            "text": "Уникальный вопрос?",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"]
        }
        
        with patch("content.validator.get_db") as mock_get_db:
            mock_db = MagicMock()
            
            mock_existing = MagicMock()
            mock_existing.id = 123
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_existing
            mock_db.execute.return_value = mock_result
            
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            issues = await validator._validate_uniqueness(question)
            
            assert len(issues) > 0
            assert "уже существует" in issues[0].message


class TestDifficultyValidation:
    """Тесты валидации сложности (Уровень 5)."""
    
    def test_invalid_difficulty(self):
        """Тест невалидной сложности."""
        validator = ContentValidator()
        question = {
            "text": "Вопрос?",
            "correct_answer": "Ответ",
            "wrong_answers": ["А", "Б", "В"],
            "difficulty": "super_hard"
        }
        
        issues = validator._validate_difficulty(question)
        
        assert any("Необычный уровень" in i.message for i in issues)


class TestFullValidation:
    """Тесты полной валидации."""
    
    @pytest.mark.asyncio
    async def test_valid_question(self, valid_question):
        """Тест полностью валидного вопроса."""
        validator = ContentValidator()
        
        with patch.object(validator, "_validate_uniqueness") as mock_unique:
            mock_unique.return_value = []
            
            report = await validator.validate_question(valid_question)
            
            assert report.is_valid == True
            assert report.score >= 70
    
    @pytest.mark.asyncio
    async def test_invalid_question(self, invalid_question):
        """Тест невалидного вопроса."""
        validator = ContentValidator()
        
        report = await validator.validate_question(invalid_question)
        
        assert report.is_valid == False
        assert len(report.get_errors()) > 0


class TestBatchValidation:
    """Тесты пакетной валидации."""
    
    @pytest.mark.asyncio
    async def test_batch_validation(self):
        """Тест валидации нескольких вопросов."""
        batch_validator = BatchValidator()
        
        questions = [
            {
                "text": "Вопрос 1?",
                "correct_answer": "Ответ 1",
                "wrong_answers": ["А", "Б", "В"],
                "category": "general",
                "difficulty": "easy"
            },
            {
                "text": "Вопрос 2?",
                "correct_answer": "Ответ 2",
                "wrong_answers": ["Г", "Д", "Е"],
                "category": "science",
                "difficulty": "medium"
            }
        ]
        
        with patch.object(batch_validator.validator, "validate_question") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                score=90,
                get_errors=lambda: [],
                get_warnings=lambda: []
            )
            
            results = await batch_validator.validate_batch(questions)
            
            assert results["total"] == 2
            assert results["valid"] == 2


class TestSimilarityCalculation:
    """Тесты расчёта схожести строк."""
    
    def test_identical_strings(self):
        """Тест идентичных строк."""
        validator = ContentValidator()
        similarity = validator._calculate_similarity("ответ", "ответ")
        
        assert similarity == 1.0
    
    def test_completely_different(self):
        """Тест совершенно разных строк."""
        validator = ContentValidator()
        similarity = validator._calculate_similarity("абвгд", "ежзий")
        
        assert similarity < 0.5
    
    def test_partial_similarity(self):
        """Тест частичной схожести."""
        validator = ContentValidator()
        similarity = validator._calculate_similarity("Париж", "париж")
        
        assert similarity > 0.5
