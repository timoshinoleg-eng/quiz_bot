from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import db
from api import app
from config import settings
from models import Question, QuizPack, QuizPackQuestion


@pytest.fixture
async def api_database(tmp_path):
    await db.close_db()
    settings.DATABASE = replace(settings.DATABASE, url=f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite3'}")
    settings.GAME = replace(settings.GAME, daily_question_count=7)
    await db.init_db()
    async with db.get_db() as session:
        pack = QuizPack(slug="space", title="Космос", short_description="Звёзды", description="Звёзды", emoji="🚀", category="science", featured=True)
        session.add(pack)
        await session.flush()
        for index in range(12):
            question = Question(text=f"Вопрос {index}?", category="science", difficulty="medium", correct_answer=f"Верно {index}", wrong_answers=[f"A {index}", f"B {index}", f"C {index}"], explanation="Факт", source="test", language="ru", verified=True)
            session.add(question)
            await session.flush()
            session.add(QuizPackQuestion(quiz_pack_id=pack.id, question_id=question.id))
    yield
    await db.close_db()


def contains_answer_key(value):
    if isinstance(value, dict):
        return any(key in {"correct_index", "correct_answer"} or contains_answer_key(item) for key, item in value.items())
    return isinstance(value, list) and any(contains_answer_key(item) for item in value)


@pytest.mark.asyncio
async def test_api_catalog_general_quick_daily_and_contract(api_database):
    with TestClient(app) as client:
        headers = {"X-Development-User": "123456"}
        catalog = client.get("/api/v1/quizzes")
        quick = client.post("/api/v1/games", headers=headers, json={"category": "general", "difficulty": "medium", "question_count": 5})
        daily = client.post("/api/v1/daily/games", headers=headers)
        invalid = client.post("/api/v1/games", headers=headers, json={"question_count": 6})
    assert catalog.status_code == 200 and catalog.json()["items"][0]["slug"] == "space"
    assert quick.status_code == 200 and quick.json()["question_count"] == 5 and not contains_answer_key(quick.json())
    assert daily.status_code == 200 and daily.json()["question_count"] == 7
    assert invalid.status_code == 422
