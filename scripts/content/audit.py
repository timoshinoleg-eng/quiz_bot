from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter
from difflib import SequenceMatcher

from sqlalchemy import func, select

from db import get_db
from models import Question, QuizPack, QuizPackQuestion


def normalise(text: str) -> str:
    return re.sub(r"[^a-zа-я0-9 ]+", "", text.lower().replace("ё", "е")).strip()


def fuzzy_duplicate_count(texts: list[str]) -> int:
    """Compare only candidates with meaningful token overlap, not every pair."""
    token_sets = [set(text.split()) for text in texts]
    count = 0
    for index, text in enumerate(texts):
        for previous, other in enumerate(texts[:index]):
            if text == other or len(token_sets[index] & token_sets[previous]) < 3:
                continue
            if SequenceMatcher(None, text, other).ratio() > 0.94:
                count += 1
    return count


async def main() -> None:
    async with get_db() as db:
        questions = list((await db.execute(select(Question))).scalars())
        packs = list((await db.execute(select(QuizPack))).scalars())
        pack_rows = (await db.execute(
            select(QuizPack.slug, func.count(Question.id))
            .join(QuizPackQuestion, QuizPackQuestion.quiz_pack_id == QuizPack.id)
            .join(Question, Question.id == QuizPackQuestion.question_id)
            .where(Question.is_active.is_(True))
            .group_by(QuizPack.slug)
        )).all()
    active = [question for question in questions if question.is_active]
    russian = [question for question in active if question.language == "ru"]
    texts = [normalise(question.text) for question in active]
    duplicates = sum(count - 1 for count in Counter(texts).values() if count > 1)
    fuzzy = fuzzy_duplicate_count(texts)
    invalid = [question for question in active if len(question.wrong_answers or []) != 3 or question.correct_answer in (question.wrong_answers or []) or len(set(question.wrong_answers or [])) != 3]
    placeholders = [question for question in active if any("вариант " in answer.lower() or "неверно" in answer.lower() for answer in question.wrong_answers or [])]
    print(
        f"Total: {len(questions)}\nActive: {len(active)}\nRussian: {len(russian)}\n"
        f"Quiz packs: {len(packs)}\nBy quiz: {dict(pack_rows)}\n"
        f"By category: {dict(Counter(question.category for question in active))}\n"
        f"By difficulty: {dict(Counter(question.difficulty for question in active))}\n"
        f"By source: {dict(Counter(question.source for question in active))}\n"
        f"Duplicates: {duplicates}\nFuzzy duplicates: {fuzzy}\nInvalid: {len(invalid)}\n"
        f"Missing explanations: {sum(not question.explanation for question in active)}\n"
        f"Placeholder distractors: {len(placeholders)}\nUnverified: {sum(not question.verified for question in active)}"
    )
    # A different preamble around the same fact is still a duplicate for a quiz
    # player. Keep this check blocking: otherwise CI can report a successful
    # content import while a round contains the same question twice.
    if len(russian) < 500 or duplicates or fuzzy or invalid or placeholders:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
