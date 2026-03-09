# scripts/distribute_questions_fixed.py
"""
Распределение вопросов по категориям на основе ключевых слов.
Исправленная версия для правильной схемы БД.
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import create_engine, update, select, func, case
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Question  # Импортируем модель

# Ключевые слова для категорий
CATEGORY_KEYWORDS = {
    'SCIENCE': ['наука', 'физика', 'химия', 'биология', 'космос', 'планета', 'учёный', 'атом', 'молекула', 'энергия', 'земля', 'солнце'],
    'HISTORY': ['история', 'война', 'царь', 'император', 'революция', 'год', 'век', 'древний', 'средневеков', 'битва', 'армия'],
    'GEOGRAPHY': ['город', 'страна', 'река', 'море', 'столица', 'континент', 'океан', 'гор', 'остров', 'материк', 'пустыня'],
    'ART': ['художник', 'картина', 'музыка', 'писатель', 'книга', 'театр', 'скульптор', 'поэт', 'стих', 'литература', 'фильм', 'кино'],
    'SPORT': ['спорт', 'футбол', 'хоккей', 'олимпиада', 'чемпион', 'команда', 'игрок', 'матч', 'гол', 'турнир', 'соревновани'],
    'TECHNOLOGY': ['компьютер', 'интернет', 'программ', 'алгоритм', 'код', 'сайт', 'приложени', 'гаджет', 'смартфон', 'технолог'],
    'NATURE': ['животн', 'растен', 'птиц', 'рыб', 'насеком', 'лес', 'природ', 'экологи', 'вид', 'популяци'],
}

async def distribute_questions():
    """Распределение вопросов по категориям."""
    
    database_url = "sqlite:///quiz_bot.db"
    engine = create_engine(database_url)
    
    updated_count = 0
    
    with Session(engine) as session:
        for category, keywords in CATEGORY_KEYWORDS.items():
            category_updated = 0
            
            for keyword in keywords:
                # Поиск вопросов по ключевому слову (используем text вместо question_text)
                stmt = (
                    update(Question)
                    .where(Question.text.ilike(f"%{keyword}%"))
                    .where(Question.category == 'GENERAL')  # Только нераспределённые
                    .values(category=category)
                )
                
                result = session.execute(stmt)
                count = result.rowcount
                
                if count > 0:
                    category_updated += count
                    print(f"  {keyword} → {category}: {count} вопросов")
            
            if category_updated > 0:
                print(f"✅ {category}: {category_updated} вопросов")
                updated_count += category_updated
                session.commit()
    
    # Финальная статистика
    print("\n=== ИТОГО ===")
    with Session(engine) as session:
        result = session.execute(
            select(Question.category, func.count(Question.id))
            .group_by(Question.category)
            .order_by(func.count(Question.id).desc())
        )
        
        for category, count in result:
            print(f"  {category}: {count}")
        
        total = session.execute(select(func.count(Question.id))).scalar()
        print(f"\n✅ Всего вопросов: {total}")
        print(f"✅ Распределено: {updated_count}")

if __name__ == "__main__":
    asyncio.run(distribute_questions())