"""Импорт вопросов по Гарри Поттеру из JSON файла."""
import json
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from db import Session
from models import Question, DifficultyLevel, QuestionCategory

def import_questions():
    """Импортировать вопросы из hp_book1_questions.json."""
    json_path = Path(__file__).parent.parent / "hp_book1_questions.json"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    session = Session()
    total = 0
    
    for difficulty, questions in data.items():
        for q in questions:
            question = Question(
                text=q["text"],
                correct_answer=q["correct_answer"],
                wrong_answers=q["wrong_answers"],
                explanation=q.get("explanation", ""),
                difficulty=DifficultyLevel(difficulty),
                category=QuestionCategory.ENTERTAINMENT,
                source="harry_potter_book_1",
                is_active=True
            )
            session.add(question)
            total += 1
    
    session.commit()
    session.close()
    
    print(f"✅ Импортировано {total} вопросов")
    
    # Вывод статистики по уровням
    session = Session()
    for d in ["easy", "medium", "hard"]:
        count = session.query(Question).filter(Question.difficulty == d).count()
        print(f"  {d}: {count} вопросов")
    session.close()

if __name__ == "__main__":
    import_questions()
