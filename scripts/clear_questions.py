"""Очистка всех вопросов из базы данных."""
from db import engine
from sqlalchemy import text

def clear_all_questions():
    """Удалить все вопросы из таблицы questions."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM questions"))
        # Сброс автоинкремента для SQLite
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name='questions'"))
        conn.commit()
    print("✅ Все старые вопросы удалены")

if __name__ == "__main__":
    clear_all_questions()
