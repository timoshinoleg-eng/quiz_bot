"""Очистка всех вопросов из базы данных (синхронная версия)."""
import sqlite3
import os

def clear_all_questions():
    """Удалить все вопросы из таблицы questions."""
    db_path = os.getenv('DATABASE_PATH', 'quiz_bot.db')
    
    # Убираем префикс async если есть
    if db_path.startswith('sqlite+aiosqlite:'):
        db_path = db_path.replace('sqlite+aiosqlite:', 'sqlite:')
    if db_path.startswith('sqlite:'):
        db_path = db_path[7:]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Удаляем все вопросы
    cursor.execute("DELETE FROM questions")
    
    # Сброс автоинкремента
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
    
    conn.commit()
    conn.close()
    
    print("✅ Все старые вопросы удалены")

if __name__ == "__main__":
    clear_all_questions()
