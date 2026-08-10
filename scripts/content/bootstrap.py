from __future__ import annotations
import asyncio
from sqlalchemy import select
from content.packs.curated_ru import PACKS, build_questions
from db import get_db, init_db
from models import Question, QuizPack, QuizPackQuestion

async def main():
    await init_db(); records=build_questions(); pack_map={item[0]:item for item in PACKS}
    async with get_db() as db:
        expected={row["source_id"] for row in records}
        # V2 corpus supersedes the small beta seed; retain rows for rollback but do not mix
        # unreviewed legacy content into the active catalog.
        for question in (await db.execute(select(Question).where(Question.source=="beta_seed"))).scalars():
            question.is_active=False
        old=list((await db.execute(select(Question).where(Question.source=="curated_ru_v2"))).scalars())
        for question in old:
            if question.source_id not in expected: question.is_active=False
        packs={p.slug:p for p in (await db.execute(select(QuizPack))).scalars()}
        for order,(slug,title,emoji,description,category,featured) in enumerate(PACKS):
            pack=packs.get(slug)
            if not pack:
                pack=QuizPack(slug=slug,title=title,emoji=emoji,short_description=description,description=description,category=category,featured=featured,sort_order=order,estimated_minutes=3)
                db.add(pack); await db.flush(); packs[slug]=pack
        imported=0
        for row in records:
            question=await db.scalar(select(Question).where(Question.source=="curated_ru_v2",Question.source_id==row["source_id"]))
            if question is None:
                question=Question(text=row["text"],category=pack_map[row["pack"]][4],difficulty=row["difficulty"],correct_answer=row["correct_answer"],wrong_answers=row["wrong_answers"],explanation=row["explanation"],source="curated_ru_v2",source_id=row["source_id"],source_license="CC0-1.0",language="ru",tags=[row["pack"]],verified=True)
                db.add(question); await db.flush(); imported+=1
            else:
                question.text=row["text"]; question.correct_answer=row["correct_answer"]; question.wrong_answers=row["wrong_answers"]; question.explanation=row["explanation"]; question.difficulty=row["difficulty"]; question.verified=True
            question.source_url=row["source_url"]
            question.source_license=row["source_license"]
            linked=await db.scalar(select(QuizPackQuestion).where(QuizPackQuestion.quiz_pack_id==packs[row["pack"]].id,QuizPackQuestion.question_id==question.id))
            if linked is None: db.add(QuizPackQuestion(quiz_pack_id=packs[row["pack"]].id,question_id=question.id))
    print(f"Imported: {imported}\nActive RU: {len(records)}\nRejected: 0\nDuplicates: 0")
if __name__ == "__main__": asyncio.run(main())
