"""Transactional importer for the audited fourth-grade Russian quiz corpus."""
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

CORPUS_PATH = Path(__file__).resolve().parents[2] / "content" / "packs" / "grade4_audited_v2.json"
SOURCE = "grade4_audited_v2"
SOURCE_LICENSE = "Source URLs recorded; rights not verified"

SUBJECTS = {
    "Русский язык": ("russian-language", "Русский язык", "📝", "russian", True),
    "Математика": ("mathematics", "Математика", "➗", "math", True),
    "Литературное чтение": ("literature", "Литературное чтение", "📚", "literature", True),
    "Окружающий мир": ("world-around", "Окружающий мир", "🌍", "world", False),
    "Английский язык": ("english", "Английский язык", "🇬🇧", "english", False),
}
DIFFICULTIES = {"лёгкий": "easy", "средний": "medium", "сложный": "hard"}


def load_questions(path: Path = CORPUS_PATH) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload.get("questions")
    if payload.get("schema_version") != "2.0" or payload.get("questions_total") != 500 or not isinstance(questions, list):
        raise ValueError("Expected the audited v2 corpus with 500 questions")
    if len(questions) != 500 or len({row.get("id") for row in questions}) != 500:
        raise ValueError("Question IDs must be complete and unique")
    texts: set[str] = set()
    for row in questions:
        subject = row.get("subject")
        options = [row.get("option_a"), row.get("option_b"), row.get("option_c"), row.get("option_d")]
        correct_letter = row.get("correct_letter")
        normalised = str(row.get("question", "")).strip().casefold()
        if (
            subject not in SUBJECTS
            or row.get("difficulty") not in DIFFICULTIES
            or not normalised
            or normalised in texts
            or any(not isinstance(option, str) or not option.strip() for option in options)
            or len(set(options)) != 4
            or row.get("correct_answer") not in options
            or correct_letter not in "ABCD"
            or options["ABCD".index(correct_letter)] != row.get("correct_answer")
            or not row.get("explanation")
            or not row.get("source_url")
        ):
            raise ValueError(f"Invalid audited question {row.get('id')}")
        texts.add(normalised)
    return questions


async def replace_content(path: Path = CORPUS_PATH) -> dict[str, int]:
    """Replace questions and the rounds/progress that reference them atomically."""
    questions = load_questions(path)
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
            subject = row["subject"]
            tags = [
                f"subject:{subject}", f"topic:{row['topic']}",
                f"format:{row.get('format_style') or 'single_choice'}",
                f"media:{row.get('media_type') or 'none'}",
            ]
            if row.get("asset_filename"):
                tags.append(f"asset:{row['asset_filename']}")
            options = [row["option_a"].strip(), row["option_b"].strip(), row["option_c"].strip(), row["option_d"].strip()]
            correct_answer = row["correct_answer"].strip()
            question = Question(
                text=row["question"].strip(), category=SUBJECTS[subject][3],
                difficulty=DIFFICULTIES[row["difficulty"]],
                correct_answer=correct_answer,
                wrong_answers=[option for option in options if option != correct_answer],
                explanation=row["explanation"].strip(), source=SOURCE,
                source_id=f"grade4-v2-{row['id']:03d}", source_url=row["source_url"].strip(),
                source_license=SOURCE_LICENSE, language="ru", tags=tags,
                age_min=10, age_max=11, verified=True, content_rating="kids", is_active=True,
            )
            session.add(question)
            await session.flush()
            session.add(QuizPackQuestion(quiz_pack_id=packs[subject].id, question_id=question.id))

    return {"removed_questions": int(old_question_count or 0), "imported_questions": len(questions), "packs": len(SUBJECTS)}


def audit_summary() -> dict[str, int]:
    questions = load_questions()
    return {
        "questions": len(questions),
        "subjects": len(Counter(row["subject"] for row in questions)),
        "media_questions": sum(row.get("media_type") not in (None, "", "none") for row in questions),
    }
