from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import func, select

import db
from config import settings
from models import Question, QuizPack, User
from scripts.content.audit import fuzzy_duplicate_count
from scripts.content.grade4_audited_v2 import (
    FIRST_WAVE_ACTION,
    SECOND_WAVE_ACTION,
    SOURCE,
    TEXT_ACTION,
    load_questions,
    load_visual_plan,
    replace_content,
    sync_approved_metadata,
)


@pytest.fixture
async def database(tmp_path):
    await db.close_db()
    settings.DATABASE = replace(settings.DATABASE, url=f"sqlite+aiosqlite:///{tmp_path / 'grade4.sqlite3'}")
    await db.init_db()
    yield
    await db.close_db()


def test_grade4_source_is_complete_and_valid():
    questions = load_questions()
    assert len(questions) == 500
    assert {question["subject"] for question in questions} == {
        "Русский язык", "Математика", "Литературное чтение", "Окружающий мир", "Английский язык",
    }


def test_approved_visual_plan_matches_questions_without_changing_answers():
    questions = load_questions()
    plan = load_visual_plan(questions)
    assert len(plan) == 179
    assert sum(item["recommended_action"] == FIRST_WAVE_ACTION for item in plan.values()) == 74
    assert sum(item["recommended_action"] == SECOND_WAVE_ACTION for item in plan.values()) == 32
    assert sum(item["recommended_action"] == TEXT_ACTION for item in plan.values()) == 73
    source = {question["id"]: question for question in questions}
    assert all(
        item["correct_answer"] == source[question_id]["correct_answer"]
        and item["correct_letter"] == source[question_id]["correct_letter"]
        for question_id, item in plan.items()
    )


def test_fuzzy_audit_keeps_distinct_quoted_entities():
    first = Question(text="Кто написал «Детство»?", category="literature", difficulty="medium", correct_answer="Л. Н. Толстой", wrong_answers=["А", "Б", "В"])
    second = Question(text="Кто написал «Черепаха»?", category="literature", difficulty="medium", correct_answer="Л. Н. Толстой", wrong_answers=["А", "Б", "В"])
    assert fuzzy_duplicate_count([first, second]) == 0


@pytest.mark.asyncio
async def test_grade4_replacement_removes_old_content_and_resets_progress(database):
    async with db.get_db() as session:
        session.add(Question(text="Старый вопрос?", category="general", difficulty="medium", correct_answer="Да", wrong_answers=["Нет", "Может быть", "Не знаю"], source="old"))
        session.add(User(id=77, xp=100, games_played=3, achievements=["old"]))
    result = await replace_content()
    assert result == {"removed_questions": 1, "imported_questions": 500, "packs": 5}
    async with db.get_db() as session:
        assert await session.scalar(select(func.count(Question.id))) == 500
        assert await session.scalar(select(func.count(QuizPack.id))) == 5
        imported = list((await session.execute(select(Question).where(Question.source == SOURCE))).scalars())
        assert len(imported) == 500
        assert all(len(question.wrong_answers) == 3 and question.correct_answer not in question.wrong_answers for question in imported)
        user = await session.get(User, 77)
        assert user is not None and user.xp == 0 and user.games_played == 0 and user.achievements == []


@pytest.mark.asyncio
async def test_approved_metadata_sync_preserves_answers_and_user_progress(database):
    await replace_content()
    async with db.get_db() as session:
        question = await session.scalar(select(Question).where(Question.source_id == "grade4-001"))
        assert question is not None
        original_answer, original_wrong = question.correct_answer, list(question.wrong_answers)
        question.source = "grade4_audited_v2"
        question.source_id = "grade4-v2-001"
        question.tags = ["media:illustration"]
        session.add(User(id=91, xp=321, games_played=4, achievements=["first_game"]))

    result = await sync_approved_metadata()
    assert result == {"updated_questions": 500, "visual_first_wave": 74, "visual_second_wave": 32, "text_only": 73}
    async with db.get_db() as session:
        question = await session.scalar(select(Question).where(Question.source_id == "grade4-001"))
        user = await session.get(User, 91)
        assert question is not None
        assert question.correct_answer == original_answer and question.wrong_answers == original_wrong
        assert "visual:mode:text" in question.tags and "media:none" in question.tags
        assert user is not None and user.xp == 321 and user.games_played == 4 and user.achievements == ["first_game"]
