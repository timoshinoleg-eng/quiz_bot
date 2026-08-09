from __future__ import annotations
import asyncio, re, sys
from collections import Counter
from difflib import SequenceMatcher
from sqlalchemy import select
from db import get_db
from models import Question, QuizPack

def normalise(text: str) -> str: return re.sub(r"[^a-zа-я0-9 ]+", "", text.lower().replace("ё","е")).strip()
async def main():
    async with get_db() as db: questions=list((await db.execute(select(Question))).scalars()); packs=list((await db.execute(select(QuizPack))).scalars())
    active=[q for q in questions if q.is_active]; ru=[q for q in active if q.language=="ru"]
    texts=[normalise(q.text) for q in active]; duplicates=sum(1 for i,text in enumerate(texts) if text in texts[:i])
    fuzzy=sum(1 for i,text in enumerate(texts) for prior in texts[:i] if text!=prior and SequenceMatcher(None,text,prior).ratio()>.94)
    invalid=[q for q in active if len(q.wrong_answers or [])!=3 or q.correct_answer in (q.wrong_answers or []) or len(set(q.wrong_answers or []))!=3]
    placeholders=[q for q in active if any("вариант " in x.lower() or "неверно" in x.lower() for x in q.wrong_answers or [])]
    print(f"Total: {len(questions)}\nActive: {len(active)}\nRussian: {len(ru)}\nQuiz packs: {len(packs)}\nBy category: {dict(Counter(q.category for q in active))}\nBy difficulty: {dict(Counter(q.difficulty for q in active))}\nBy source: {dict(Counter(q.source for q in active))}\nDuplicates: {duplicates}\nFuzzy duplicates: {fuzzy}\nInvalid: {len(invalid)}\nMissing explanations: {sum(not q.explanation for q in active)}\nPlaceholder distractors: {len(placeholders)}\nUnverified: {sum(not q.verified for q in active)}")
    if len(ru)<500 or invalid or placeholders: sys.exit(1)
if __name__=="__main__": asyncio.run(main())
