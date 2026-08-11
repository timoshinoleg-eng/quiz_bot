"""Validated importer for the approved fourth-grade quiz and visual plan."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from sqlalchemy import delete, func, select, update

from db import get_db
from models import (
    AnalyticsEvent,
    ChallengeAttempt,
    ChallengeQuestion,
    DailyChallenge,
    DailyQuestion,
    DailyResult,
    FriendChallenge,
    Game,
    GameQuestion,
    Question,
    QuizPack,
    QuizPackQuestion,
    User,
    UserQuestionHistory,
)

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"
CORPUS_PATH = CONTENT_DIR / "quiz_grade4.json"
VISUAL_PLAN_PATH = CONTENT_DIR / "visual_plan_grade4.json"
SOURCE = "quiz_grade4_core_plus_starred_v1"
SOURCE_LICENSE = "Source URLs recorded; rights not verified"

SUBJECTS = {
    "Русский язык": ("russian-language", "Русский язык", "📝", "russian", True),
    "Математика": ("mathematics", "Математика", "➗", "math", True),
    "Литературное чтение": ("literature", "Литературное чтение", "📚", "literature", True),
    "Окружающий мир": ("world-around", "Окружающий мир", "🌍", "world", False),
    "Английский язык": ("english", "Английский язык", "🇬🇧", "english", False),
}
DIFFICULTIES = {"лёгкий": "easy", "средний": "medium", "сложный": "hard"}
TEXT_ACTION = "перевести в текстовый формат"
FIRST_WAVE_ACTION = "генерировать в 1-й волне"
SECOND_WAVE_ACTION = "оставить в резерве / 2-я волна"


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read approved content file {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Approved content file {path} must be a JSON object")
    return payload


def _options(row: dict) -> list[str]:
    return [str(row.get(f"option_{letter}", "")).strip() for letter in "abcd"]


def _validate_question(row: dict, seen_texts: set[str]) -> None:
    subject = row.get("subject")
    options = _options(row)
    answer = str(row.get("correct_answer", "")).strip()
    correct_letter = row.get("correct_letter")
    normalised = str(row.get("question", "")).strip().casefold()
    if (
        subject not in SUBJECTS
        or row.get("difficulty") not in DIFFICULTIES
        or not isinstance(row.get("id"), int)
        or not normalised
        or normalised in seen_texts
        or any(not option for option in options)
        or len(set(options)) != 4
        or answer not in options
        or not isinstance(correct_letter, str)
        or correct_letter not in "ABCD"
        or options["ABCD".index(correct_letter)] != answer
        or not str(row.get("explanation", "")).strip()
        or not str(row.get("source_url", "")).strip()
    ):
        raise ValueError(f"Invalid approved question {row.get('id')}")
    seen_texts.add(normalised)


def load_questions(path: Path = CORPUS_PATH) -> list[dict]:
    """Load the approved core and starred question lists without editing answers."""
    payload = _read_json(path)
    core = payload.get("core_questions")
    starred = payload.get("starred_questions")
    summary = payload.get("summary")
    if (
        payload.get("schema_version") != "3.0"
        or not isinstance(core, list)
        or not isinstance(starred, list)
        or not isinstance(summary, dict)
        or summary.get("total_questions") != 500
        or summary.get("core_questions") != 492
        or summary.get("starred_questions") != 8
    ):
        raise ValueError("Expected the approved 500-question Grade 4 corpus")
    questions = sorted([*core, *starred], key=lambda row: row.get("id", 0))
    if len(questions) != 500 or len({row.get("id") for row in questions}) != 500:
        raise ValueError("Approved question IDs must be complete and unique")
    if set(summary.get("starred_ids", [])) != {row.get("id") for row in starred}:
        raise ValueError("Starred-question metadata does not match the approved corpus")
    seen_texts: set[str] = set()
    for row in questions:
        _validate_question(row, seen_texts)
    return questions


def load_visual_plan(questions: list[dict], path: Path = VISUAL_PLAN_PATH) -> dict[int, dict]:
    """Validate that the approved plan cannot override a question or its answer."""
    payload = _read_json(path)
    rows = payload.get("visual_plan")
    expected_priorities = {"A": 74, "B": 32, "C": 73}
    if (
        payload.get("schema_version") != "2.0"
        or payload.get("source_core_questions") != 492
        or payload.get("priority_counts") != expected_priorities
        or not isinstance(rows, list)
        or len(rows) != sum(expected_priorities.values())
    ):
        raise ValueError("Expected the approved Grade 4 visual plan")
    question_by_id = {row["id"]: row for row in questions}
    plan_by_id = {row.get("id"): row for row in rows}
    if len(plan_by_id) != len(rows) or not set(plan_by_id).issubset(question_by_id):
        raise ValueError("Visual-plan IDs must be unique approved question IDs")
    starred_ids = {row["id"] for row in questions if row.get("star_reason")}
    if not set(payload.get("removed_star_visual_ids", [])).issubset(starred_ids):
        raise ValueError("Visual-plan removed IDs must refer to starred questions")
    for question_id, plan in plan_by_id.items():
        question = question_by_id[question_id]
        for field in ("subject", "topic", "question", "difficulty", "correct_answer", "correct_letter", "source_url", "option_a", "option_b", "option_c", "option_d"):
            if plan.get(field) != question.get(field):
                raise ValueError(f"Visual plan attempts to change approved field {field} for question {question_id}")
        if plan.get("recommended_action") not in {TEXT_ACTION, FIRST_WAVE_ACTION, SECOND_WAVE_ACTION}:
            raise ValueError(f"Unknown visual-plan action for question {question_id}")
        if plan.get("priority") not in expected_priorities:
            raise ValueError(f"Unknown visual priority for question {question_id}")
    return plan_by_id


def question_tags(row: dict, visual_plan: dict[int, dict]) -> list[str]:
    """Return non-answer metadata; image assets remain absent until supplied separately."""
    plan = visual_plan.get(row["id"])
    if plan is None:
        media_type, visual_mode = "none", "not_planned"
    elif plan["recommended_action"] == TEXT_ACTION:
        media_type, visual_mode = "none", "text"
    elif plan["recommended_action"] == FIRST_WAVE_ACTION:
        media_type, visual_mode = plan["current_media_type"], "first_wave"
    else:
        media_type, visual_mode = plan["current_media_type"], "second_wave"
    tags = [
        f"subject:{row['subject']}",
        f"topic:{row['topic']}",
        f"format:{row.get('format_style') or 'single_choice'}",
        f"media:{media_type}",
        f"visual:mode:{visual_mode}",
        f"program:{row.get('program_track') or 'Основная программа 4 класса'}",
    ]
    if plan is not None:
        tags.extend((f"visual:priority:{plan['priority']}", f"visual:type:{plan['recommended_visual_type']}"))
    if row.get("star_reason"):
        tags.append("content:starred")
    return tags


def _matches_approved_content(question: Question, row: dict) -> bool:
    source_options = _options(row)
    expected_wrong = [option for option in source_options if option != row["correct_answer"]]
    return (
        question.text == row["question"].strip()
        and question.correct_answer == row["correct_answer"].strip()
        and sorted(question.wrong_answers or []) == sorted(expected_wrong)
        and question.explanation == row["explanation"].strip()
    )


def _apply_metadata(question: Question, row: dict, visual_plan: dict[int, dict]) -> None:
    question.source = SOURCE
    question.source_id = f"grade4-{row['id']:03d}"
    question.source_url = row["source_url"].strip()
    question.source_license = SOURCE_LICENSE
    question.language = "ru"
    question.tags = question_tags(row, visual_plan)
    question.age_min = 10
    question.age_max = 11
    question.verified = True
    question.content_rating = "kids"
    question.is_active = True


async def sync_approved_metadata() -> dict[str, int]:
    """Attach approved source/visual metadata without changing questions or user progress."""
    rows = load_questions()
    visual_plan = load_visual_plan(rows)
    row_by_id = {row["id"]: row for row in rows}
    updated = 0
    async with get_db() as session:
        active_questions = list((await session.execute(select(Question).where(Question.is_active.is_(True)))).scalars())
        if len(active_questions) != len(rows):
            raise ValueError("Active database corpus differs from the approved 500-question corpus; run the replacement bootstrap")
        for question in active_questions:
            source_id = str(question.source_id or "")
            try:
                question_id = int(source_id.rsplit("-", 1)[-1])
            except ValueError as error:
                raise ValueError("Active database question has no approved Grade 4 source ID; run the replacement bootstrap") from error
            row = row_by_id.get(question_id)
            if row is None or not _matches_approved_content(question, row):
                raise ValueError(f"Database content differs from approved question {question_id}; no answer was changed")
            _apply_metadata(question, row, visual_plan)
            updated += 1
    return {"updated_questions": updated, "visual_first_wave": sum(plan["recommended_action"] == FIRST_WAVE_ACTION for plan in visual_plan.values()), "visual_second_wave": sum(plan["recommended_action"] == SECOND_WAVE_ACTION for plan in visual_plan.values()), "text_only": sum(plan["recommended_action"] == TEXT_ACTION for plan in visual_plan.values())}


async def replace_content(path: Path = CORPUS_PATH) -> dict[str, int]:
    """Replace questions and dependent rounds/progress with the approved corpus."""
    questions = load_questions(path)
    visual_plan = load_visual_plan(questions)
    async with get_db() as session:
        old_question_count = await session.scalar(select(func.count(Question.id)))
        await session.execute(delete(DailyResult))
        await session.execute(delete(ChallengeAttempt))
        await session.execute(delete(GameQuestion))
        await session.execute(delete(DailyQuestion))
        await session.execute(delete(ChallengeQuestion))
        await session.execute(delete(UserQuestionHistory))
        await session.execute(delete(Game))
        await session.execute(update(FriendChallenge).values(rematch_of=None))
        await session.execute(delete(FriendChallenge))
        await session.execute(delete(DailyChallenge))
        await session.execute(delete(QuizPackQuestion))
        await session.execute(delete(Question))
        await session.execute(delete(QuizPack))
        await session.execute(delete(AnalyticsEvent))
        await session.execute(update(User).values(
            score_total=0, games_played=0, games_won=0, xp=0, level=1,
            daily_streak=0, best_streak=0, last_daily_date=None,
            achievements=[], current_state=None, state_data={},
        ))

        packs: dict[str, QuizPack] = {}
        for order, (subject, (slug, title, emoji, category, featured)) in enumerate(SUBJECTS.items()):
            pack = QuizPack(
                slug=slug, title=title, emoji=emoji,
                short_description=f"4 класс · {subject}",
                description=f"Проверенный набор: {subject}, 4 класс (10–11 лет).",
                category=category, language="ru", age_min=10, age_max=11,
                featured=featured, active=True, sort_order=order, estimated_minutes=4,
            )
            session.add(pack)
            await session.flush()
            packs[subject] = pack

        for row in questions:
            options = _options(row)
            correct_answer = row["correct_answer"].strip()
            question = Question(
                text=row["question"].strip(), category=SUBJECTS[row["subject"]][3],
                difficulty=DIFFICULTIES[row["difficulty"]], correct_answer=correct_answer,
                wrong_answers=[option for option in options if option != correct_answer],
                explanation=row["explanation"].strip(), source=SOURCE,
                source_id=f"grade4-{row['id']:03d}", source_url=row["source_url"].strip(),
                source_license=SOURCE_LICENSE, language="ru", tags=question_tags(row, visual_plan),
                age_min=10, age_max=11, verified=True, content_rating="kids", is_active=True,
            )
            session.add(question)
            await session.flush()
            session.add(QuizPackQuestion(quiz_pack_id=packs[row["subject"]].id, question_id=question.id))

    return {"removed_questions": int(old_question_count or 0), "imported_questions": len(questions), "packs": len(SUBJECTS)}


def audit_summary() -> dict[str, int]:
    questions = load_questions()
    visual_plan = load_visual_plan(questions)
    return {
        "questions": len(questions),
        "subjects": len(Counter(row["subject"] for row in questions)),
        "visual_first_wave": sum(plan["recommended_action"] == FIRST_WAVE_ACTION for plan in visual_plan.values()),
        "visual_second_wave": sum(plan["recommended_action"] == SECOND_WAVE_ACTION for plan in visual_plan.values()),
        "text_only": sum(plan["recommended_action"] == TEXT_ACTION for plan in visual_plan.values()),
    }
