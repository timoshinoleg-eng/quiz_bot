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


def fuzzy_duplicate_count(questions: list[Question]) -> int:
    """Count reworded copies of the same knowledge check.

    A near-identical template alone is not a duplicate: multiplication examples
    and vocabulary cards deliberately share grammar while checking different
    answers.  A blocking near-duplicate must therefore have both a close stem
    and the same normalised answer (or the same answer-option set).
    """
    texts = [normalise(question.text) for question in questions]
    answers = [normalise(question.correct_answer) for question in questions]
    option_sets = [frozenset(normalise(value) for value in [question.correct_answer, *(question.wrong_answers or [])]) for question in questions]
    token_sets = [set(text.split()) for text in texts]
    quoted_entities = [set(re.findall(r"«([^»]+)»", question.text.casefold())) for question in questions]
    count = 0
    for index, text in enumerate(texts):
        for previous, other in enumerate(texts[:index]):
            if text == other or len(token_sets[index] & token_sets[previous]) < 3:
                continue
            # Reused classroom wording can intentionally ask about different,
            # explicitly named works or terms. Those are distinct facts even
            # when the author/answer options happen to coincide.
            if quoted_entities[index] and quoted_entities[previous] and quoted_entities[index] != quoted_entities[previous]:
                continue
            if answers[index] != answers[previous] and option_sets[index] != option_sets[previous]:
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
    fuzzy = fuzzy_duplicate_count(active)
    invalid = [question for question in active if len(question.wrong_answers or []) != 3 or question.correct_answer in (question.wrong_answers or []) or len(set(question.wrong_answers or [])) != 3]
    placeholders = [question for question in active if any("вариант " in answer.lower() or "неверно" in answer.lower() for answer in question.wrong_answers or [])]
    missing_provenance = [question for question in active if not question.source_url or not question.source_license]
    print(
        f"Total: {len(questions)}\nActive: {len(active)}\nRussian: {len(russian)}\n"
        f"Quiz packs: {len(packs)}\nBy quiz: {dict(pack_rows)}\n"
        f"By category: {dict(Counter(question.category for question in active))}\n"
        f"By difficulty: {dict(Counter(question.difficulty for question in active))}\n"
        f"By source: {dict(Counter(question.source for question in active))}\n"
        f"Duplicates: {duplicates}\nFuzzy duplicates: {fuzzy}\nInvalid: {len(invalid)}\n"
        f"Missing explanations: {sum(not question.explanation for question in active)}\n"
        f"Placeholder distractors: {len(placeholders)}\nMissing provenance: {len(missing_provenance)}\n"
        f"Unverified: {sum(not question.verified for question in active)}"
    )
    # A different preamble around the same fact is still a duplicate for a quiz
    # player. Keep this check blocking: otherwise CI can report a successful
    # content import while a round contains the same question twice.
    if len(russian) < 500 or duplicates or fuzzy or invalid or placeholders or missing_provenance:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
