"""Load a small validated JSON question pack into the configured database."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import close_db, get_db, init_db
from models import Question


async def load(path: Path) -> tuple[int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Question pack must be a JSON array")
    loaded = skipped = 0
    async with get_db() as session:
        for item in data:
            text = str(item.get("text", "")).strip()
            correct = str(item.get("correct_answer", "")).strip()
            wrong = [str(value).strip() for value in item.get("wrong_answers", []) if str(value).strip()]
            if not text or not correct or len(wrong) != 3 or correct in wrong:
                raise ValueError(f"Invalid question: {item!r}")
            exists = await session.scalar(select(Question).where(Question.text == text))
            if exists:
                skipped += 1
                continue
            session.add(Question(
                text=text,
                category=str(item.get("category", "general")),
                difficulty=str(item.get("difficulty", "easy")),
                correct_answer=correct,
                wrong_answers=wrong,
                explanation=item.get("explanation"),
                source=str(item.get("source", "beta_seed")),
            ))
            loaded += 1
    return loaded, skipped


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=Path("content/beta_seed.json"))
    args = parser.parse_args()
    await init_db()
    try:
        loaded, skipped = await load(args.file)
        print(f"loaded={loaded} skipped={skipped}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
