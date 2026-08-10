from dataclasses import replace

import pytest

import db
from config import settings
from models import Question


@pytest.fixture
async def v2_database(tmp_path):
    await db.close_db()
    settings.DATABASE = replace(settings.DATABASE, url=f"sqlite+aiosqlite:///{tmp_path / 'v2.sqlite3'}")
    settings.GAME = replace(settings.GAME, daily_question_count=7)
    await db.init_db()
    async with db.get_db() as session:
        for index in range(12):
            session.add(Question(text=f"Вопрос науки {index}?", category="science", difficulty="medium", correct_answer=f"Ответ {index}", wrong_answers=[f"A {index}",f"B {index}",f"C {index}"], source="test", language="ru", verified=True))
    yield
    await db.close_db()


@pytest.mark.asyncio
async def test_v2_general_mode_draws_from_concrete_packs_and_daily_has_seven_questions(v2_database):
    await db.db_manager.get_or_create_user(700)
    quick=await db.db_manager.create_game(700,"general","medium",5)
    daily=await db.db_manager.create_daily_game(700)
    assert quick.question_count==5
    assert daily.question_count==7
    assert len(await db.db_manager.get_game_questions(daily.id))==7
