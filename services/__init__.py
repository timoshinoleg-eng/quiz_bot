"""Services package for MAX-Квиз."""

# Импортируем только безопасные модули
try:
    from .question_formatter import QuestionFormatter
except ImportError:
    QuestionFormatter = None

__all__ = [
    "QuestionFormatter",
]
