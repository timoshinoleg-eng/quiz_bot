"""Asynchronous Friend Challenge application service."""

from typing import Any, Optional

from db import ChallengeError, db_manager


async def create(user_id: int, category: str = "general", difficulty: str = "medium", count: int = 5,
                rematch_of: Optional[int] = None):
    return await db_manager.create_challenge(user_id, category, difficulty, count, rematch_of)


async def join(code: str, user_id: int):
    return await db_manager.join_challenge(code, user_id)


async def summary(challenge_id: int):
    return await db_manager.get_challenge_summary(challenge_id)


__all__ = ["ChallengeError", "create", "join", "summary"]
